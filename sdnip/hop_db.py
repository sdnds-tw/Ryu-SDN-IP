
class HopDB(object):

    def __init__(self):
        super(HopDB, self).__init__()
        self.hops = {}  # prefix -> hop
        self.installed_prefix = []

    def add_hop(self, prefix, next_hop):
        self.hops.setdefault(prefix, next_hop)

    def get_nexthop(self, prefix):
        self.hops.get(prefix)

    def is_prefix_installed(self, prefix):
        return (prefix in self.installed_prefix)

    def get_uninstalled_prefix_list(self):
        result = [prefix for prefix in
                  self.hops.keys() if (prefix not in self.installed_prefix)]
        return result

    def install_prefix(self, prefix):
        self.installed_prefix.append(prefix)

    def get_all_prefixes(self):
        return self.hops.keys()

    def withdraw(self, prefix):

        if prefix in self.hops:
            self.hops.pop(prefix)

        if prefix in self.installed_prefix:
            self.installed_prefix.remove(prefix)
