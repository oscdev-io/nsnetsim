"""Tests for ExaBGP."""


from nsnetsim.topology import Topology
from nsnetsim.exabgp_router_node import ExaBGPRouterNode
from nsnetsim.switch_node import SwitchNode


class TestExaBGPRouterNode:
    """Test the ExaBGPRouterNode class."""

    def test_basic_config(self):
        """Test one router with a configuration file."""

        topology = Topology()

        router_x = ExaBGPRouterNode("routerX", configfile="tests/exabgp_router_node/routerX.conf")
        topology.add_node(router_x)
        router_x_eth0 = router_x.add_interface("eth0", mac="02:01:00:00:00:01")
        router_x_eth0.add_ip(["192.168.0.1/24", "fec0::1/64"])

        switch_1 = SwitchNode("switch1")
        topology.add_node(switch_1)
        switch_1.add_interface(router_x_eth0)

        topology.run()
        topology.destroy()
