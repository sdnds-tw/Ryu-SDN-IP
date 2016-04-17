from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v3_0
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.services.protocols.bgp.bgpspeaker import BGPSpeaker
from .conf_mgr import SDNIPConfigManager


class SDNIP(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNIP, self).__init__(*args, **kwargs)
        self.cfg_mgr = SDNIPConfigManager('config.json')
        self.logger.info("Creating speaker with as number: {}, router id: {}, port: {}",
                         self.cfg_mgr.as_number, self.cfg_mgr.router_id, self.cfg_mgr.listen_port)
        self.bgp_speaker = BGPSpeaker(self.cfg_mgr.as_number, self.cfg_mgr.router_id,
                 bgp_server_port=self.cfg_mgr.listen_port,
                 best_path_change_handler=self.best_path_change_handler,
                 peer_down_handler=self.peer_down_handler,
                 peer_up_handler=self.peer_up_handler)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is not None and \
           eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

    def best_path_change_handler(self, ev):
        self.logger.debug('best path changed:')
        self.logger.debug('remote_as: {}', ev.remote_as)
        self.logger.debug('route_dist: {}', ev.route_dist)
        self.logger.debug('prefix: {}', ev.prefix)
        self.logger.debug('nexthop: {}', ev.nexthop)
        self.logger.debug('label: {}', ev.label)
        self.logger.debug('is_withdraw: {}', ev.is_withdraw)

    def peer_down_handler(self, ev):
        self.logger.debug('peer down:')
        self.logger.debug('remote_as: {}', ev.remote_as)
        self.logger.debug('route_dist: {}', ev.route_dist)
        self.logger.debug('prefix: {}', ev.prefix)
        self.logger.debug('nexthop: {}', ev.nexthop)
        self.logger.debug('label: {}', ev.label)
        self.logger.debug('is_withdraw: {}', ev.is_withdraw)

    def peer_up_handler(self, ev):
        self.logger.debug('peer up:')
        self.logger.debug('remote_as: {}', ev.remote_as)
        self.logger.debug('route_dist: {}', ev.route_dist)
        self.logger.debug('prefix: {}', ev.prefix)
        self.logger.debug('nexthop: {}', ev.nexthop)
        self.logger.debug('label: {}', ev.label)
        self.logger.debug('is_withdraw: {}', ev.is_withdraw)
