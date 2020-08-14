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

"""Switch node support."""

import subprocess
from typing import List

from .generic_node import GenericNode
from .namespace_network_interface import NamespaceNetworkInterface


class SwitchNode(GenericNode):
    """Switch implements a basic switch support for nsnetsim."""

    # Name of the bridge we've created
    _bridge_name: str
    # Interfaces added to this switch
    _interfaces: List[NamespaceNetworkInterface]

    def _init(self, **kwargs):
        """Initialize the object."""

        name = kwargs.get("name")

        # Set the bridge name we're going to use
        self._bridge_name = f"sw-{name}"

        # Start out with no interfaces added to this switch\
        self._interfaces = []

    def _create(self):
        """Create the switch."""

        subprocess.check_call(["ip", "link", "add", self.bridge_name, "type", "bridge", "forward_delay", "0"])
        subprocess.check_call(["ip", "link", "set", self.bridge_name, "up"])

        # Add interfaces to the bridge by setting the bridge as the interface master
        for interface in self.interfaces:
            self._log(f'Adding interface "{interface.name}" from "{interface.namespace.name}" ' f'to switch "{self.name}"')
            subprocess.check_call(["ip", "link", "set", interface.ifname_host, "master", self.bridge_name])

    def _remove(self):
        """Remove the namespace."""

        try:
            subprocess.check_call(["ip", "link", "del", self.bridge_name])
        except subprocess.CalledProcessError:
            self._log(f'WARNING: Failed to remove switch "{self.bridge_name}"')

    def add_interface(self, interface: NamespaceNetworkInterface):
        """Add an interface to this switch."""

        # Add an interface to the list we have of interfaces
        self._interfaces.append(interface)

    @property
    def bridge_name(self):
        """Return the bridge name of this switch."""
        return self._bridge_name

    @property
    def interfaces(self):
        """Return the interfaces linked to this switch."""
        return self._interfaces
