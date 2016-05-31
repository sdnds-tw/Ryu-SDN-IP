import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import in_proto
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import ether_types
from ryu.topology import api as topo_api
from .conf_mgr import SDNIPConfigManager
from .fwd import Fwd


class FwdBGP(app_manager.RyuApp):
    '''
    Foward BGP packet to internal BGP speakers
    '''
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'fwd': Fwd
    }

    def __init__(self, *args, **kwargs):
        super(FwdBGP, self).__init__(*args, **kwargs)
        self.cfg_mgr = SDNIPConfigManager()
        self.fwd = kwargs['fwd']

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

        if tcp_header is None or (tcp_header.src_port is not 179 and
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
        dst_mac = dst_host.mac
        to_dst_match = dp.ofproto_parser.OFPMatch(eth_dst=dst_mac,
                                                  ipv4_dst=dst_ip,
                                                  eth_type=2048)

        port_no = self.fwd.setup_shortest_path(src_port.dpid,
                                               dst_port.dpid,
                                               dst_port.port_no,
                                               to_dst_match)

        if port_no is None:
            # Can't find path to destination, ignore it.
            return

        self.packet_out(dp, msg, port_no)

    def packet_out(self, dp, msg, out_port):
        ofproto = dp.ofproto
        actions = [dp.ofproto_parser.OFPActionOutput(out_port)]
        out = dp.ofproto_parser.OFPPacketOut(
            datapath=dp, in_port=msg.match['in_port'],
            buffer_id=ofproto.OFP_NO_BUFFER,
            actions=actions, data=msg.data)
        dp.send_msg(out)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=priority,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)
