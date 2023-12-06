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

"""Topology support."""

import logging
from typing import Dict, List, Optional

from .exceptions import NsNetSimError
from .generic_node import GenericNode
from .router_node import RouterNode
from .switch_node import SwitchNode


class Topology:
    """Topology implements the high level simulation setup."""

    # Our list of nodes
    _nodes: List[GenericNode]
    # Switches by name
    _nodes_by_name: Dict[str, GenericNode]

    def __init__(self):
        """Initialize the object."""

        # Clear the lists of nodes we have
        self._nodes = []
        self._nodes_by_name = {}

    def add_node(self, node: GenericNode):
        """Add a router to our topology."""

        node_type = type(node).__name__

        logging.info("Adding node: [%s] %s", node_type, node.name)

        # Check if router exists.. if so throw an error
        if node.name in self._nodes_by_name:
            raise RuntimeError(f'Router node "{node.name}" already exists')

        self._nodes_by_name[node.name] = node
        self._nodes.append(node)

    def run(self):
        """Build our simulated network."""

        logging.info("Build and run a topology")
        try:
            # We need to create routers first, so they're up before we plug them into switches
            for node in self._nodes:
                if isinstance(node, RouterNode):
                    node.create()
            # Then switches
            for node in self._nodes:
                if isinstance(node, SwitchNode):
                    node.create()
        except NsNetSimError as err:
            logging.error("Simulation error: %s", err)
            self.destroy()
            raise NsNetSimError(f"Simulation error: {err}") from None

    def destroy(self):
        """Destroy our simulated network."""

        logging.info("Destroying topology")
        # We need to remove routers first
        for node in self._nodes:
            if isinstance(node, RouterNode):
                node.remove()
        # Then switches
        for node in self._nodes:
            if isinstance(node, SwitchNode):
                node.remove()

    def node(self, name: str) -> Optional[GenericNode]:
        """Return a node with a given name."""
        if name in self._nodes_by_name:
            return self._nodes_by_name[name]
        # Or None if not found
        return None
