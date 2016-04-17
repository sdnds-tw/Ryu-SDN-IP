import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import in_proto
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import ether_types
from ryu.topology import api as topo_api
from conf_mgr import SDNIPConfigManager


class FwdBGP(app_manager.RyuApp):
    '''
    Foward BGP packet to internal BGP speakers
    '''
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FwdBGP, self).__init__(*args, **kwargs)
        self.cfg_mgr = SDNIPConfigManager('config.json')

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofproto = dp.ofproto

        pkt = packet.Packet(msg.data)
        tcp_header = pkt.get_protocol(tcp.tcp)

        if tcp_header is None or \
           (tcp_header.src_port is not 179 and \
           tcp_header.dst_port is not 179):
            # ignore non-BGP packet
            return

        ipv4_header = pkt.get_protocol(ipv4.ipv4)
        src_ip = ipv4_header.src
        dst_ip = ipv4_header.dst
        self.logger.info("BGP from %s to %s", src_ip, dst_ip)

        # create a path from src to dst
        hosts = topo_api.get_all_host(self)
        src_host = None
        dst_host = None

        for host in hosts:
            if src_ip in host.ipv4:
                src_host = host

            elif dst_ip in host.ipv4:
                dst_host = host

        if src_host is None or dst_host is None:
            # can't find src or dst, drop it
            return

        src_port = src_host.port
        dst_port = dst_host.port
        nx_grapth = self.get_nx_graph()
        path = self.get_shortest_path(nx_grapth, src_port.dpid, dst_port.dpid)

        if path is None:
            # path doesn't exist, drop it
            return

        dst_mac = dst_host.mac
        to_dst_match = dp.ofproto_parser.OFPMatch(eth_dst=dst_mac, ipv4_dst=dst_ip, eth_type=2048, tcp_dst=179)

        if len(path) == 1:
            # src and dst are in same switch
            port_no = dst_port.port_no
            actions = [dp.ofproto_parser.OFPActionOutput(port_no)]
            self.add_flow(dp, to_dst_match, actions)

            self.packet_out(dp, msg, port_no)

        else:
            self.install_path(to_dst_match, path, nx_grapth)

            # install to last dp
            dst_dpid = dst_port.dpid
            dst_dp = self.get_datapath(dst_dpid)
            dst_port_no = dst_port.port_no
            actions = [dst_dp.ofproto_parser.OFPActionOutput(dst_port_no)]
            self.add_flow(dst_dp, to_dst_match, actions)

            # packet out
            port_no = nx_grapth.edge[path[0]][path[1]]['src_port']
            self.packet_out(dp, msg, port_no)


    def get_shortest_path(self, nx_graph, src_dpid, dst_dpid):

        if nx.has_path(nx_graph, src_dpid, dst_dpid):
            return nx.shortest_path(nx_graph, src_dpid, dst_dpid)

        return None

    def packet_out(self, dp, msg, out_port):
        ofproto = dp.ofproto
        actions = [dp.ofproto_parser.OFPActionOutput(out_port)]
        out = dp.ofproto_parser.OFPPacketOut(
            datapath=dp, in_port=msg.in_port, buffer_id=ofproto.OFP_NO_BUFFER,
            actions=actions, data=msg.data)
        dp.send_msg(out)

    def get_nx_graph(self):
        graph = nx.DiGraph()
        switches = topo_api.get_all_switch(self)
        links = topo_api.get_all_link(self)

        for switch in switches:
            dpid = switch.dp.id
            graph.add_node(dpid)

        for link in links:
            src_dpid = link.src.dpid
            dst_dpid = link.dst.dpid
            src_port = link.src.port_no
            dst_port = link.dst.port_no
            graph.add_edge(src_dpid, dst_dpid, src_port=src_port, dst_port=dst_port)
        return graph

    def install_path(self, match, path, nx_graph):
        '''
        path : [1, 2, 3]
        '''
        for index, dpid in enumerate(path[:-1]):
            # edge[path[index]][path[index + 1]]
            # => path[index] to path[index+1] port
            port_no = nx_graph.edge[path[index]][path[index + 1]]['src_port']
            dp = self.get_datapath(dpid)
            actions = [dp.ofproto_parser.OFPActionOutput(port_no)]
            self.add_flow(dp, match, actions)

    def add_flow(self, datapath, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=inst)
        datapath.send_msg(mod)
