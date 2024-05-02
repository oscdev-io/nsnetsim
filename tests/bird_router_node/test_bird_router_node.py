#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2019-2024, AllWorldIT.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for BIRD."""

import re
import time
from typing import Any

from nsnetsim.bird_router_node import BirdRouterNode
from nsnetsim.switch_node import SwitchNode
from nsnetsim.topology import Topology

__all__ = ["TestBirdRouterNode"]


class CustomPytestRegex:
    """Assert that a given string meets some expectations."""

    _pattern: str

    def __init__(self, pattern: str, flags: int = 0) -> None:
        """Inititalize object."""
        self._pattern = pattern
        self._regex = re.compile(pattern, flags)

    def __eq__(self, actual: Any) -> bool:
        """Check if the 'actual' string matches the regex."""
        print(f"COMPARE: {self._pattern}")
        print(f"COMPARE: {actual}")
        return bool(self._regex.match(actual))

    def __repr__(self) -> Any:
        """Return our representation."""
        return self._regex.pattern


class TestBirdRouterNode:
    """Test the BirdRouterNode class."""

    def test_basic_config(self) -> None:
        """Test one router with a configuration file."""

        topology = Topology()

        # Add router
        topology.add_node(BirdRouterNode("r1", configfile="tests/bird_router_node/r1.conf"))
        node_r1 = topology.node("r1")
        if not isinstance(node_r1, BirdRouterNode):
            raise RuntimeError("Node r1 not found")
        node_r1.add_interface("eth0", mac="02:01:00:00:00:01", ips=["192.168.0.1/24", "fec0::1/64"])
        node_r1_iface = node_r1.interface("eth0")
        if not node_r1_iface:
            raise RuntimeError("Interface eth0 not found")

        # Add switch
        topology.add_node(SwitchNode("s1"))
        node_s1 = topology.node("s1")
        if not isinstance(node_s1, SwitchNode):
            raise RuntimeError("Node s1 not found")
        node_s1.add_interface(node_r1_iface)

        topology.run()

        status_output = node_r1.birdc_show_status()

        topology.destroy()

        assert "router_id" in status_output, 'The status output should have "router_id"'
        assert status_output["router_id"] == "192.168.0.1", 'The router ID should be "192.168.0.1"'

    def test_rip(self) -> None:  # pylint: disable=too-many-statements
        """Test a two router setup with RIP."""

        topology = Topology()

        # Add router r1
        topology.add_node(BirdRouterNode("r1", configfile="tests/bird_router_node/r1.conf"))
        node_r1 = topology.node("r1")
        if not isinstance(node_r1, BirdRouterNode):
            raise RuntimeError("Node r1 not found")
        # Add interfaces
        node_r1.add_interface("eth0", mac="02:01:00:00:00:01", ips=["192.168.0.1/24", "fec0::1/64"])
        node_r1_eth0 = node_r1.interface("eth0")
        if not node_r1_eth0:
            raise RuntimeError("Interface eth0 not found")
        node_r1.add_interface("eth1", mac="02:01:01:00:00:01", ips=["192.168.10.1/24", "fec0:10::1/64"])
        node_r1_eth1 = node_r1.interface("eth1")
        if not node_r1_eth1:
            raise RuntimeError("Interface eth1 not found")

        # Add router r2
        topology.add_node(BirdRouterNode("r2", configfile="tests/bird_router_node/r2.conf"))
        node_r2 = topology.node("r2")
        if not isinstance(node_r2, BirdRouterNode):
            raise RuntimeError("Node r2 not found")
        # Add interface
        node_r2.add_interface("eth0", mac="02:02:00:00:00:01", ips=["192.168.0.2/24", "fec0::2/64"])
        node_r2_eth0 = node_r2.interface("eth0")
        if not node_r2_eth0:
            raise RuntimeError("Interface eth0 not found")

        # Add switch
        topology.add_node(SwitchNode("s1"))
        node_s1 = topology.node("s1")
        if not isinstance(node_s1, SwitchNode):
            raise RuntimeError("Node s1 not found")

        node_s1.add_interface(node_r1_eth0)
        node_s1.add_interface(node_r2_eth0)

        topology.run()

        try:
            routerx_protocols_output = node_r1.birdc_show_protocols()
            routery_protocols_output = node_r2.birdc_show_protocols()

            time.sleep(10)
            routerx_master4_output = node_r1.birdc_show_route_table("master4")
            routery_master4_output = node_r2.birdc_show_route_table("master4")

            routerx_symbols_output = node_r1.birdc("show symbols table")
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
            CustomPytestRegex(r"(?:1010-| )?master[46] \trouting table"),
            CustomPytestRegex(r"(?:1010-| )?master[46] \trouting table"),
            "0000 ",
        ]
        assert routerx_symbols_output == routerx_protocol_expected, "Protocol output does not match what it should"
