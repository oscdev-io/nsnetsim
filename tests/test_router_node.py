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


from nsnetsim.router_node import RouterNode
from nsnetsim.switch_node import SwitchNode
from nsnetsim.topology import Topology

__all__ = ["TestRouterNode"]


class TestRouterNode:  # pylint: disable=too-few-public-methods
    """Test the BirdNode class."""

    def test_basic(self) -> None:
        """Test a basic namespace router."""

        topology = Topology()

        # Router
        topology.add_node(RouterNode("r1"))
        node_r1 = topology.node("r1")

        if not isinstance(node_r1, RouterNode):
            raise RuntimeError("Node r1 not found")
        node_r1.add_interface("eth0", mac="02:01:00:00:00:01", ips=["192.168.0.1/24", "fec0::1/64"])
        node_r1.add_route(["192.168.90.0/24", "via", "192.168.0.2"])
        node_r1.add_route(["fec0:10::/64", "via", "fec0::2"])
        # Grab interface
        node_r1_iface = node_r1.interface("eth0")
        if not node_r1_iface:
            raise RuntimeError("Interface eth0 not found")

        # Switch
        topology.add_node(SwitchNode("s1"))
        node_s1 = topology.node("s1")

        if not isinstance(node_s1, SwitchNode):
            raise RuntimeError("Node s1 not found")
        node_s1.add_interface(node_r1_iface)

        topology.run()

        try:
            result_routes_v4 = node_r1.run_ip(["--family", "inet", "route", "list"])
            result_routes_v6 = node_r1.run_ip(["--family", "inet6", "route", "list"])
        finally:
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
