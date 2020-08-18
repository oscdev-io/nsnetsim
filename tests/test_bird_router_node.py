"""Tests for BIRD."""

import re
import time

from nsnetsim.topology import Topology
from nsnetsim.bird_router_node import BirdRouterNode
from nsnetsim.switch_node import SwitchNode


class CustomPytestRegex:
    """Assert that a given string meets some expectations."""

    def __init__(self, pattern, flags=0):
        """Inititalize object."""
        self._regex = re.compile(pattern, flags)

    def __eq__(self, actual):
        """Check if the 'actual' string matches the regex."""
        return bool(self._regex.match(actual))

    def __repr__(self):
        """Return our representation."""
        return self._regex.pattern


class TestBirdRouterNode:
    """Test the BirdRouterNode class."""

    def test_basic_config(self):
        """Test one router with a configuration file."""

        topology = Topology()

        router_x = BirdRouterNode("routerX", configfile="tests/bird_router_node/routerX.conf")
        topology.add_node(router_x)
        router_x_eth0 = router_x.add_interface("eth0", mac="02:01:00:00:00:01")
        router_x_eth0.add_ip(["192.168.0.1/24", "fec0::1/64"])

        switch_1 = SwitchNode("switch1")
        topology.add_node(switch_1)
        switch_1.add_interface(router_x_eth0)

        topology.run()

        status_output = router_x.birdc_show_status()

        topology.destroy()

        assert "router_id" in status_output, 'The status output should have "router_id"'
        assert status_output["router_id"] == "192.168.0.1", 'The router ID should be "192.168.0.1"'

    def test_rip(self):
        """Test a two router setup with RIP."""

        topology = Topology()

        router_x = BirdRouterNode("routerX", configfile="tests/bird_router_node/routerX.conf")
        topology.add_node(router_x)
        router_x_eth0 = router_x.add_interface("eth0", mac="02:01:00:00:00:01")
        router_x_eth0.add_ip(["192.168.0.1/24", "fec0::1/64"])
        router_x_eth1 = router_x.add_interface("eth1", mac="02:01:01:00:00:01")
        router_x_eth1.add_ip(["192.168.10.1/24", "fec0:10::1/64"])

        router_y = BirdRouterNode("routerY", configfile="tests/bird_router_node/routerY.conf")
        topology.add_node(router_y)
        router_y_eth0 = router_y.add_interface("eth0", mac="02:02:00:00:00:01")
        router_y_eth0.add_ip(["192.168.0.2/24", "fec0::2/64"])

        switch_1 = SwitchNode("switch1")
        topology.add_node(switch_1)
        switch_1.add_interface(router_x_eth0)
        switch_1.add_interface(router_y_eth0)

        topology.run()

        try:
            routerx_protocols_output = router_x.birdc_show_protocols()
            routery_protocols_output = router_y.birdc_show_protocols()

            time.sleep(10)
            routerx_master4_output = router_x.birdc_show_route_table("master4")
            routery_master4_output = router_y.birdc_show_route_table("master4")

            routerx_symbols_output = router_x.birdc("show symbols table")
        finally:
            topology.destroy()

        assert "rip4" in routerx_protocols_output, 'The "rip4" protocol should be in the protocols output'
        assert "rip6" in routerx_protocols_output, 'The "rip6" protocol should be in the protocols output'
        assert routerx_protocols_output["rip4"]["state"] == "up", 'The "rip4" protocol should be in state "up"'
        assert routerx_protocols_output["rip6"]["state"] == "up", 'The "rip6" protocol should be in state "up"'

        print(f"PROTOCOLSX: {routerx_protocols_output}")
        print(f"PROTOCOLSY: {routery_protocols_output}")

        print(f"MASTER4X: {routerx_master4_output}")
        print(f"MASTER4Y: {routery_master4_output}")

        assert len(routerx_master4_output) == 1, "There should be one route on routerX"
        assert "192.168.10.0/24" in routerx_master4_output, 'The route in routerX master4 must be "192.168.10.0/24"'
        assert (
            routerx_master4_output["192.168.10.0/24"][0]["protocol"] == "rip4_direct"
        ), 'The route in routerX master4 must be proto "rip4_direct"'

        assert len(routery_master4_output) == 1, "There should be one route on routerY"
        assert "192.168.10.0/24" in routery_master4_output, 'The route in routerY master4 must be "192.168.10.0/24"'
        assert (
            routery_master4_output["192.168.10.0/24"][0]["protocol"] == "rip4"
        ), 'The route in routerY master4 must be proto "rip4"'
        assert routery_master4_output["192.168.10.0/24"][0]["nexthops"] == [
            {"gateway": "192.168.0.1", "interface": "eth0"}
        ], 'The "gateway" should be "192.168.0.1"'

        routerx_protocol_expected = [
            CustomPytestRegex(r"0001 BIRD [0-9\.]+ ready."),
            "1010-master4 \trouting table",
            " master6 \trouting table",
            "0000 ",
        ]
        assert routerx_symbols_output == routerx_protocol_expected, "Protocol output does not match what it should"
