
class HopDB(object):

    def __init__(self):
        super(HopDB, self).__init__()
        self.hops = {}  # prefix -> hop

    def add_hop(self, prefix, next_hop):
        self.hops.setdefault(prefix, next_hop)
