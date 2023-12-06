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

"""Tests for ExaBGP."""


from nsnetsim.topology import Topology
from nsnetsim.exabgp_router_node import ExaBGPRouterNode
from nsnetsim.switch_node import SwitchNode


class TestExaBGPRouterNode:
    """Test the ExaBGPRouterNode class."""

    def test_basic_config(self):
        """Test one router with a configuration file."""

        topology = Topology()

        topology.add_node(ExaBGPRouterNode("r1", configfile="tests/exabgp_router_node/r1.conf"))
        topology.node("r1").add_interface("eth0", mac="02:01:00:00:00:01", ips=["192.168.0.1/24", "fec0::1/64"])

        topology.add_node(SwitchNode("s1"))
        topology.node("s1").add_interface(topology.node("r1").interface("eth0"))

        topology.run()
        topology.destroy()
