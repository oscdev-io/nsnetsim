"""Tests for BIRD."""


from nsnetsim.topology import Topology
from nsnetsim.bird_router_node import RouterNode
from nsnetsim.switch_node import SwitchNode


class TestRouterNode:
    """Test the BirdNode class."""

    def test_basic(self):
        """Test a basic namespace router."""

        topology = Topology()

        router_x = RouterNode("routerX")
        topology.add_node(router_x)
        router_x_eth0 = router_x.add_interface("eth0", mac="02:01:00:00:00:01")
        router_x_eth0.add_ip(["192.168.0.1/24", "fec0::1/64"])

        router_x.add_route(["192.168.90.0/24", "via", "192.168.0.2"])
        router_x.add_route(["fec0:10::/64", "via", "fec0::2"])

        switch_1 = SwitchNode("switch1")
        topology.add_node(switch_1)
        switch_1.add_interface(router_x_eth0)

        topology.run()

        result_routes_v4 = router_x.run_ip(["--family", "inet", "route", "list"])
        result_routes_v6 = router_x.run_ip(["--family", "inet6", "route", "list"])

        topology.destroy()

        #
        # Routing tests
        #

        correct_routes_v4 = [
            {"dst": "192.168.0.0/24", "dev": "eth0", "protocol": "kernel", "scope": "link", "prefsrc": "192.168.0.1", "flags": []},
            {"dst": "192.168.90.0/24", "gateway": "192.168.0.2", "dev": "eth0", "flags": []},
        ]
        correct_routes_v6 = [
            {"dst": "fe80::/64", "dev": "eth0", "protocol": "kernel", "metric": 256, "pref": "medium", "flags": []},
            {"dst": "fec0::/64", "dev": "eth0", "protocol": "kernel", "metric": 256, "pref": "medium", "flags": []},
            {"dst": "fec0:10::/64", "gateway": "fec0::2", "dev": "eth0", "metric": 1024, "pref": "medium", "flags": []},
        ]

        assert result_routes_v4 == correct_routes_v4, "Routing table for IPv4 does not match expected value"
        assert result_routes_v6 == correct_routes_v6, "Routing table for IPv6 does not match expected value"
