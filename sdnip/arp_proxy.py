import json
from ryu import cfg
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from ryu.lib.ofp_pktinfilter import packet_in_filter, RequiredTypeFilter
from .conf_mgr import SDNIPConfigManager

CONF = cfg.CONF
CONF.register_cli_opts([
    cfg.StrOpt('static-arp-table',
               default=None,
               help='location of SDN-IP config file')
])


class ArpProxy(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ArpProxy, self).__init__(*args, **kwargs)
        self.cfg_mgr = SDNIPConfigManager()
        self.arp_table = {}

        if CONF.static_arp_table is not None:
            # load static arp table
            static_arp_table = json.load(open(CONF.static_arp_table, "r"))

            for record in static_arp_table:
                self.arp_table.setdefault(record['ip'], record['mac'])

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    @packet_in_filter(RequiredTypeFilter, {'types': [ipv4.ipv4]})
    def ipv4_packet_in_handler(self, ev):
        msg = ev.msg
        pkt = packet.Packet(msg.data)
        eth_header = pkt.get_protocol(ethernet.ethernet)
        ipv4_header = pkt.get_protocol(ipv4.ipv4)
        self.arp_table.setdefault(ipv4_header.src, eth_header.src)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    @packet_in_filter(RequiredTypeFilter, {'types': [arp.arp]})
    def arp_packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt = packet.Packet(msg.data)
        arp_header = pkt.get_protocol(arp.arp)
        src_ip = arp_header.src_ip
        src_mac = arp_header.src_mac
        dst_ip = arp_header.dst_ip
        dst_mac = None

        if self.cfg_mgr.is_internal_host(src_ip):
            # if internal host sent arp request, reply router mac address
            first_speaker_id = None

            if self.cfg_mgr.get_all_speaker_id():
                first_speaker_id = self.cfg_mgr.get_all_speaker_id()[0]

            if first_speaker_id:
                dst_mac = self.cfg_mgr.get_speaker_mac(first_speaker_id)
        else:
            dst_mac = self.arp_table.get(dst_ip)

        self.arp_table.setdefault(src_ip, src_mac)

        if arp_header.opcode != arp.ARP_REQUEST:
            return

        if not dst_mac:
            # can't find distination, drop it
            return

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
