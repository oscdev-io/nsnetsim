#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2019-2025, AllWorldIT.
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

"""Tests for StayRTR."""

from nsnetsim.stayrtr_server_node import StayRTRServerNode
from nsnetsim.switch_node import SwitchNode
from nsnetsim.topology import Topology

__all__ = ["TestStayRTRServerNode"]


class TestStayRTRServerNode:  # pylint: disable=too-few-public-methods
    """Test the StayRTRServerNode class."""

    def test_basic_config(self) -> None:
        """Test one router with a configuration file."""

        topology = Topology()

        # Add node
        topology.add_node(StayRTRServerNode("r1", configfile="tests/stayrtr_server_node/a1.conf"))
        node_r1 = topology.node("r1")
        if not isinstance(node_r1, StayRTRServerNode):
            raise RuntimeError("Node r1 not found")
        # Add interface
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
        topology.destroy()
