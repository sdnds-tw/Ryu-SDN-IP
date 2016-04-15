import json

class SDNIPConfigManager(object):

    def __init__(self, config_file_path):
        super(ConfigManager, self).__init__()
        self.config_file_path = config_file_path
        self.per_id = {}
        self.per_dpid = {}
        speakers = []
        with open(self.config_file_path, 'r') as config_file:
            speakers = json.load(config_file)

        for speaker in speakers:
            dpid = speaker['dpid']
            port = speaker['port']
            speaker_ids = speaker['speaker_ids']
            self.per_dpid.setdeafult(dpid, [])

            for speaker_id in speaker_ids:
                self.per_id.setdefault(speaker_id, {'dpid': dpid, 'port': port})
                self.per_dpid[dpid].append({'port': port, 'id': speaker_id})

    def reload_config(self):

        self.per_id = {}
        self.per_dpid = {}
        speakers = []
        with open(self.config_file_path, 'r') as config_file:
            speakers = json.load(config_file)

        for speaker in speakers:
            dpid = speaker['dpid']
            port = speaker['port']
            speaker_ids = speaker['speaker_ids']
            self.per_dpid.setdeafult(dpid, [])

            for speaker_id in speaker_ids:
                self.per_id.setdefault(speaker_id, {'dpid': dpid, 'port': port})
                self.per_dpid[dpid].append({'port': port, 'id': speaker_id})

    def get_speaker_connect_port(self, bgp_speaker_id):
        return self.per_id.get(bgp_speaker_id)

    def get_all_speaker_id(self):
        return self.per_id.keys()

    def get_all_speakers_by_dpid(self, dpid):
        return self.per_dpid[dpid]
