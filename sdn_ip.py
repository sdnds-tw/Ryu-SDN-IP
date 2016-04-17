from netaddr import IPNetwork
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import api as topo_api
from ryu.services.protocols.bgp.bgpspeaker import BGPSpeaker
from conf_mgr import SDNIPConfigManager
from fwd import Fwd

class SDNIP(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'fwd': Fwd
    }
    def __init__(self, *args, **kwargs):
        super(SDNIP, self).__init__(*args, **kwargs)
        self.fwd = kwargs['fwd']
        self.cfg_mgr = SDNIPConfigManager('config.json')
        self.logger.info("Creating speaker with as number: %d, router id: %s, port: %d",
                         self.cfg_mgr.as_number, self.cfg_mgr.router_id, self.cfg_mgr.listen_port)
        self.bgp_speaker = BGPSpeaker(self.cfg_mgr.as_number, self.cfg_mgr.router_id,
                 bgp_server_port=self.cfg_mgr.listen_port,
                 best_path_change_handler=self.best_path_change_handler,
                 peer_down_handler=self.peer_down_handler,
                 peer_up_handler=self.peer_up_handler)

        speaker_ids = self.cfg_mgr.get_all_speaker_id()

        for speaker_id in speaker_ids:
            self.bgp_speaker.neighbor_add(speaker_id, self.cfg_mgr.as_number, is_next_hop_self=True)

    def best_path_change_handler(self, ev):
        self.logger.info('best path changed:')
        self.logger.info('remote_as: %d', ev.remote_as)
        self.logger.info('route_dist: %s', ev.route_dist)
        self.logger.info('prefix: %s', ev.prefix)
        self.logger.info('nexthop: %s', ev.nexthop)
        self.logger.info('label: %s', ev.label)
        self.logger.info('is_withdraw: %s', ev.is_withdraw)
        self.logger.info('')
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

    def install_best_path(self, prefix, nexthop):

        speaker_ids = self.cfg_mgr.get_all_speaker_id()
        nexthop_port = self.cfg_mgr.get_speaker_connect_port(nexthop)
        nexthop_mac = self.cfg_mgr.get_speaker_mac(nexthop)
        nexthop_dpid = nexthop_port['dpid']
        nexthop_port_no = nexthop_port['port']
        prefix_ip = str(IPNetwork(prefix).ip)
        prefix_mask = str(IPNetwork(prefix).netmask)


        for speaker_id in speaker_ids

            if speaker_id == nexthop:
                continue

            speaker_port = self.cfg_mgr.get_speaker_connect_port(speaker_id)
            speaker_dpid = port['dpid']
            speaker_port_no = port['port']
            dp = fwd.get_datapath(speaker_dpid)
            nexthop_match = dp.ofproto_parser.OFPMatch(ipv4_dst=(prefix_ip, prefix_mask), eth_type=2048)
            pre_actions = [dp.ofproto_parser.OFPActionSetField(eth_dst=nexthop_mac)]

            self.fwf.setup_shortest_path(speaker_dpid, nexthop_dpid, nexthop_port, nexthop_match, pre_actions)
