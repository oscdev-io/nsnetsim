#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2019-2023, AllWorldIT.
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

        topology.add_node(BirdRouterNode("r1", configfile="tests/bird_router_node/r1.conf"))
        topology.node("r1").add_interface("eth0", mac="02:01:00:00:00:01", ips=["192.168.0.1/24", "fec0::1/64"])

        topology.add_node(SwitchNode("s1"))
        topology.node("s1").add_interface(topology.node("r1").interface("eth0"))

        topology.run()

        status_output = topology.node("r1").birdc_show_status()

        topology.destroy()

        assert "router_id" in status_output, 'The status output should have "router_id"'
        assert status_output["router_id"] == "192.168.0.1", 'The router ID should be "192.168.0.1"'

    def test_rip(self):
        """Test a two router setup with RIP."""

        topology = Topology()

        topology.add_node(BirdRouterNode("r1", configfile="tests/bird_router_node/r1.conf"))
        topology.node("r1").add_interface("eth0", mac="02:01:00:00:00:01", ips=["192.168.0.1/24", "fec0::1/64"])
        topology.node("r1").add_interface("eth1", mac="02:01:01:00:00:01", ips=["192.168.10.1/24", "fec0:10::1/64"])

        topology.add_node(BirdRouterNode("r2", configfile="tests/bird_router_node/r2.conf"))
        topology.node("r2").add_interface("eth0", mac="02:02:00:00:00:01", ips=["192.168.0.2/24", "fec0::2/64"])

        topology.add_node(SwitchNode("s1"))
        topology.node("s1").add_interface(topology.node("r1").interface("eth0"))
        topology.node("s1").add_interface(topology.node("r2").interface("eth0"))

        topology.run()

        try:
            routerx_protocols_output = topology.node("r1").birdc_show_protocols()
            routery_protocols_output = topology.node("r2").birdc_show_protocols()

            time.sleep(10)
            routerx_master4_output = topology.node("r1").birdc_show_route_table("master4")
            routery_master4_output = topology.node("r2").birdc_show_route_table("master4")

            routerx_symbols_output = topology.node("r1").birdc("show symbols table")
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
