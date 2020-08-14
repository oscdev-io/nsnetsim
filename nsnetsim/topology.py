# Copyright (C) 2019, AllWorldIT.
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

from typing import Dict, List, Optional

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

    def add_router(self, name: str, router_class: RouterNode = RouterNode, **kwargs) -> RouterNode:
        """Add a router to our topology."""

        # Grab the router class name
        router_class_name = type(router_class).__name__
        self.log(f'Adding router: [{router_class_name}] {name}')

        # Check if router exists.. if so throw an error
        if name in self._nodes_by_name:
            raise RuntimeError(f'Router node "{name}" already exists')

        # Instantiate it as an object
        router = router_class(name, logger=self.log, **kwargs)

        self._nodes_by_name[name] = router
        self._nodes.append(router)

        return router

    def add_switch(self, name: str) -> SwitchNode:
        """Add a switch to our topology."""

        self.log(f'Adding switch: {name}')

        # Check if router exists.. if so throw an error
        if name in self._nodes_by_name:
            raise RuntimeError(f'Switch node "{name}" already exists')

        switch = SwitchNode(name, logger=self.log)

        self._nodes_by_name[name] = switch
        self._nodes.append(switch)

        return switch

    def build(self):
        """Build our simulated network."""

        self.log(f'Building topology')
        # We need to create routers first
        for node in self._nodes:
            if isinstance(node, RouterNode):
                node.create()
        # Then switches
        for node in self._nodes:
            if isinstance(node, SwitchNode):
                node.create()

    def destroy(self):
        """Destroy our simulated network."""

        self.log(f'Destroying topology')
        # We need to remove routers first
        for node in self._nodes:
            if isinstance(node, RouterNode):
                node.remove()
        # Then switches
        for node in self._nodes:
            if isinstance(node, SwitchNode):
                node.remove()

    def get_node(self, name: str) -> Optional[GenericNode]:
        """Return a node with a given name."""
        if name in self._nodes_by_name:
            return self._nodes_by_name[name]
        # Or None if not found
        return None

    def log(self, msg: str):
        """Log a message."""

        print(f'LOG: {msg}')
