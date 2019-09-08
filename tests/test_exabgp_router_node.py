"""Tests for ExaBGP."""


from nsnetsim.topology import Topology
from nsnetsim.exabgp_router_node import ExaBGPRouterNode


class TestExaBGPRouterNode():
    """Test the ExaBGPRouterNode class."""

    def test_basic_config(self):
        """Test one router with a configuration file."""

        topology = Topology()

        router_x = topology.add_router('routerX', router_class=ExaBGPRouterNode,
                                       configfile='tests/exabgp_router_node/routerX.conf')
        router_x_eth0 = router_x.add_interface('eth0', mac='02:01:00:00:00:01')
        router_x_eth0.add_ip(['192.168.0.1/24', 'fec0::1/64'])

        switch_1 = topology.add_switch('switch1')
        switch_1.add_interface(router_x_eth0)

        topology.build()
        topology.destroy()
