'''
DB for sroting path

Structure of ip_to_dp:
{
    'ip(/mask) 1': {
        'dpid 1': [outport1, outport2, ....](set),
        ...
    },
    ....
}

dp_to_ip:
{
    'dpid 1' {
        'ip(/mask) 1': [outport1, outport2, ....](set),
    }
}
'''

class PathDB(object):

    def __init__(self):
        super(PathDB, self).__init__()
        self.ip_to_dp = {}
        self.dp_to_ip = {}

    def add_outport(self, ip_mask, dpid, outport):
        self.ip_to_dp.setdefault(ip_mask, {})
        self.ip_to_dp[ip_mask].setdefault(dpid, set())
        self.ip_to_dp[ip_mask][dpid].add(outport)

        self.dp_to_ip.setdefault(dpid, {})
        self.dp_to_ip[dpid].setdefault(ip_mask, [])
        self.dp_to_ip[dpid][ip_mask].add(outport)

    def get_outports_by_ip(self, ip_mask):
        return self.ip_to_dp.get(ip_mask, {})

    def get_ips_by_outport(self, dpid, outport):
         return self.ip_d
