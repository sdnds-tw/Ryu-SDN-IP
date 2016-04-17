import networkx as nx



class Fwd(app_manager.RyuApp):
    '''
    Forward utilization
    '''
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FwdBGP, self).__init__(*args, **kwargs)
        self.dps = {}

    def setup_shortest_path(self, from_dpid, to_dpid, to_port_no, to_dst_match, pre_actions=[]):
        nx_grapth = self.get_nx_graph()
        path = self.get_shortest_path(nx_grapth, from_dpid, to_dpid)

        if path is None:
            # path doesn't exist, drop it
            return
        port_no = 0
        if len(path) == 1:
            # src and dst are in same switch
            dp = self.get_datapath(from_dpid)
            actions = [dp.ofproto_parser.OFPActionOutput(to_port_no)]
            self.add_flow(dp, 1, to_dst_match, pre_actions+actions)
            port_no = to_port_no
        else:
            self.install_path(to_dst_match, path, nx_grapth, pre_actions)

            # install to last dp
            dst_dp = self.get_datapath(to_dpid)
            actions = [dst_dp.ofproto_parser.OFPActionOutput(to_port_no)]
            self.add_flow(dst_dp, 1, to_dst_match, pre_actions+actions)

            # packet out
            port_no = nx_grapth.edge[path[0]][path[1]]['src_port']

        return port_no


    def get_shortest_path(self, nx_graph, src_dpid, dst_dpid):

        if nx.has_path(nx_graph, src_dpid, dst_dpid):
            return nx.shortest_path(nx_graph, src_dpid, dst_dpid)

        return None

    def get_nx_graph(self):
        graph = nx.DiGraph()
        switches = topo_api.get_all_switch(self)
        links = topo_api.get_all_link(self)

        for switch in switches:
            dpid = switch.dp.id
            graph.add_node(dpid)

        for link in links:
            src_dpid = link.src.dpid
            dst_dpid = link.dst.dpid
            src_port = link.src.port_no
            dst_port = link.dst.port_no
            graph.add_edge(src_dpid, dst_dpid, src_port=src_port, dst_port=dst_port)
        return graph

    def install_path(self, match, path, nx_graph, pre_actions=[]):
        '''
        path : [1, 2, 3]
        '''
        for index, dpid in enumerate(path[:-1]):
            # edge[path[index]][path[index + 1]]
            # => path[index] to path[index+1] port
            port_no = nx_graph.edge[path[index]][path[index + 1]]['src_port']
            dp = self.get_datapath(dpid)
            actions = [dp.ofproto_parser.OFPActionOutput(port_no)]
            self.add_flow(dp, 1, match, pre_actions+actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    def get_datapath(self, dpid):
        if dpid not in self.dps:
            switch = topo_api.get_switch(self, dpid)[0]
            self.dps[dpid] = switch.dp
            return switch.dp

        return self.dps[dpid]
