from netaddr import IPNetwork
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import api as topo_api
from ryu.services.protocols.bgp.bgpspeaker import BGPSpeaker
from conf_mgr import SDNIPConfigManager
from fwd import Fwd
from hop_db import HopDB


class SDNIP(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'fwd': Fwd,
        'hop_db': HopDB
    }

    def __init__(self, *args, **kwargs):
        super(SDNIP, self).__init__(*args, **kwargs)
        self.fwd = kwargs['fwd']
        self.hop_db = kwargs['hop_db']
        self.cfg_mgr = SDNIPConfigManager('config.json')
        self.bgp_speaker =\
        BGPSpeaker(self.cfg_mgr.as_number,
                   str(self.cfg_mgr.router_id),
                   bgp_server_port=self.cfg_mgr.listen_port,
                   best_path_change_handler=self.best_path_change_handler,
                   peer_down_handler=self.peer_down_handler,
                   peer_up_handler=self.peer_up_handler)

        speaker_ids = self.cfg_mgr.get_all_speaker_id()

        for speaker_id in speaker_ids:
            self.bgp_speaker.neighbor_add(speaker_id,
                                          self.cfg_mgr.as_number,
                                          is_next_hop_self=True)

        hub.spawn(self.prefix_check_loop)

    def best_path_change_handler(self, ev):
        self.logger.info('best path changed:')
        self.logger.info('remote_as: %d', ev.remote_as)
        self.logger.info('route_dist: %s', ev.route_dist)
        self.logger.info('prefix: %s', ev.prefix)
        self.logger.info('nexthop: %s', ev.nexthop)
        self.logger.info('label: %s', ev.label)
        self.logger.info('is_withdraw: %s', ev.is_withdraw)
        self.logger.info('')
        self.hop_db.add_hop(ev.prefix, ev.nexthop)
        self.install_best_path(ev.prefix, ev.nexthop)

    def peer_down_handler(self, remote_ip, remote_as):
        self.logger.info('peer down:')
        self.logger.info('remote_as: %d', remote_as)
        self.logger.info('remote ip: %s', remote_ip)
        self.logger.info('')

    def peer_up_handler(self, remote_ip, remote_as):
        self.logger.info('peer up:')
        self.logger.info('remote_as: %d', remote_as)
        self.logger.info('remote ip: %s', remote_ip)
        self.logger.info('')

    def get_host(self, ip):
        hosts = topo_api.get_all_host(self)

        for host in hosts:
            if ip in host.ipv4:
                return host

        return None

    def prefix_check_loop(self):

        while True:
            prefixs_to_install = self.hop_db.get_uninstalled_prefix_list()
            self.logger.debug("prefix to install: %s", str(prefixs_to_install))

            for prefix in prefixs_to_install:
                nexthop = self.hop_db.get_nexthop(prefix)
                self.install_best_path(prefix, nexthop)

            hub.sleep(3)

    def install_best_path(self, prefix, nexthop):

        nexthop_host = self.get_host(nexthop)
        self.logger.debug("nexthop host: %s", str(nexthop_host))
        if nexthop_host is None:
            return

        nexthop_port = nexthop_host.port
        nexthop_mac = nexthop_host.mac
        nexthop_dpid = nexthop_port.dpid
        nexthop_port_no = nexthop_port.port_no
        prefix_ip = str(IPNetwork(prefix).ip)
        prefix_mask = str(IPNetwork(prefix).netmask)

        for dp in self.fwd.get_all_datapaths():
            from_dpid = dp.id
            nexthop_match =\
            dp.ofproto_parser.OFPMatch(ipv4_dst=(prefix_ip, prefix_mask),
                                       eth_type=2048)
            pre_actions = [
                dp.ofproto_parser.OFPActionSetField(eth_dst=nexthop_mac)
                ]

            self.fwd.setup_shortest_path(from_dpid,
                                         nexthop_dpid,
                                         nexthop_port_no,
                                         nexthop_match,
                                         pre_actions)

        self.hop_db.install_prefix(prefix)

    def install_internal_host_path(self, ip):
        host = self.get_host(ip)

        if host is None:
            return

        for dp in self.fwd.get_all_datapaths():
            from_dpid = dp.id
            host_match =\
            dp.ofproto_parser.OFPMatch(ipv4_dst=ip,
                                       eth_type=2048)
            pre_actions = [
                dp.ofproto_parser.OFPActionSetField(eth_dst=host.mac)
                ]

            self.fwd.setup_shortest_path(from_dpid,
                                         host.port.dpid,
                                         host.port.port_no,
                                         host_match,
                                         pre_actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def internal_host_route_handler(self, ev):
        '''
        Handle internal network host routing
        '''
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofproto = dp.ofproto

        pkt = packet.Packet(msg.data)
        ipv4_header = pkt.get_protocol(ipv4.ipv4)

        if ipv4_header == None:
            return

        src_ip = ipv4_header.src
        dst_ip = ipv4_header.dst

        if not self.cfg_mgr.is_internal_host(dst_ip):
            return

        install_internal_host_path(dst_ip)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def internal_host_arp_proxy(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype != ether_types.ETH_TYPE_ARP:
            # ignore non-arp packet
            return

        arp_header = pkt.get_protocol(arp.arp)
        src_ip = arp_header.src_ip
        src_mac = arp_header.src_mac
        dst_ip = arp_header.dst_ip
        if arp_header.opcode != arp.ARP_REQUEST:
            return

        # Use first bgp speaker as gateway
        # reply first bgp speaker's mac address
        # TODO: TBD
        speaker_ids = self.cfg_mgr.get_all_speaker_id()

        if not speaker_ids:
            # no speaker to use
            return

        dst_mac = self.cfg_mgr.get_speaker_mac(speaker_ids[0])
        # send arp request to host
        actions = [parser.OFPActionOutput(in_port)]
        arp_reply = packet.Packet()
        arp_reply.add_protocol(
            ethernet.ethernet(
                ethertype=ether_types.ETH_TYPE_ARP,
                src=dst_mac,
                dst=src_mac
            )
        )
        arp_reply.add_protocol(
            arp.arp(
                opcode=arp.ARP_REPLY,
                src_ip=dst_ip,
                src_mac=dst_mac,
                dst_ip=src_ip,
                dst_mac=src_mac
            )
        )
        arp_reply.serialize()

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=ofproto.OFPP_CONTROLLER,
            actions=actions, data=arp_reply.data)
        datapath.send_msg(out)
