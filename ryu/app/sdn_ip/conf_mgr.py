import json
from ryu import cfg
from netaddr import IPNetwork

CONF = cfg.CONF

CONF.register_cli_opts([
    cfg.StrOpt('sdn-ip-cfg-file',
               default="/usr/local/etc/ryu-sdn-ip/config.json",
               help='location of SDN-IP config file')
])


class SDNIPConfigManager(object):

    def __init__(self, config_file_path):
        super(SDNIPConfigManager, self).__init__()
        self.config_file_path = CONF.sdn_ip_cfg_file
        self.reload_config()

    def reload_config(self):

        self.per_id = {}
        self.per_dpid = {}
        speakers = []
        with open(self.config_file_path, 'r') as config_file:
            configs = json.load(config_file)

        speakers = configs['speakers']
        local_config = configs['local']
        self.as_number = local_config.get('as_number', 65113)
        self.router_id = local_config.get('router_id', '127.0.0.1')
        self.listen_port = local_config.get('listen_port', 2000)
        self.networks = local_config.get('networks', [])

        for speaker in speakers:
            dpid = speaker['dpid']
            port = speaker['port']
            mac = speaker['mac']
            speaker_ids = speaker['speaker_ids']
            self.per_dpid.setdefault(dpid, [])

            for speaker_id in speaker_ids:
                self.per_id.setdefault(speaker_id,
                                       {'dpid': dpid,
                                        'port': port,
                                        'mac': mac})
                self.per_dpid[dpid].append({'port': port,
                                            'id': speaker_id,
                                            'mac': mac})

    def get_speaker_connect_port(self, bgp_speaker_id):
        return self.per_id.get(bgp_speaker_id)

    def get_all_speaker_id(self):
        return self.per_id.keys()

    def get_all_speakers_by_dpid(self, dpid):
        return self.per_dpid[dpid]

    def get_speaker_mac(self, bgp_speaker_id):
        return self.per_id.get(bgp_speaker_id)['mac']

    def is_internal_host(self, ip):

        for network in self.networks:
            nw = IPNetwork(network)
            if ip in nw:
                return True

        return False

    def get_internal_networks(self):
        return self.networks
