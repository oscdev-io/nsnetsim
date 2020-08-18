#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2019-2020, AllWorldIT.
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

import subprocess  # nosec
from typing import List

from .generic_node import GenericNode
from .exceptions import NsNetSimError
from .namespace_network_interface import NamespaceNetworkInterface


class SwitchNode(GenericNode):
    """Switch implements a basic switch support for nsnetsim."""

    # Name of the bridge we've created
    _bridge_name: str
    # Interfaces added to this switch
    _interfaces: List[NamespaceNetworkInterface]
    # Created flag
    _created: bool

    def _init(self, **kwargs):
        """Initialize the object."""

        name = kwargs.get("name")

        # Set the bridge name we're going to use
        self._bridge_name = f"sw-{name}"

        # Start out with no interfaces added to this switch\
        self._interfaces = []

        # Indicator that the bridge interface was created
        self._created = False

    def _create(self):
        """Create the switch."""

        try:
            self.run_check_call(["/usr/bin/ip", "link", "add", self.bridge_name, "type", "bridge", "forward_delay", "0"])
        except subprocess.CalledProcessError as err:
            raise NsNetSimError(f"Failed to add bridge '{self.bridge_name}' to host: {err.stdout}") from None
        # Indicate that the bridge was created
        self._created = True

        try:
            self.run_check_call(["/usr/bin/ip", "link", "set", self.bridge_name, "up"])
        except subprocess.CalledProcessError as err:
            raise NsNetSimError(f"Failed to set bridge '{self.bridge_name}' up: {err.stdout}") from None

        # Add interfaces to the bridge by setting the bridge as the interface master
        for interface in self.interfaces:
            self._log(f"Adding interface '{interface.name}' from '{interface.namespace_node.name}' to switch '{self.name}'")
            try:
                self.run_check_call(["/usr/bin/ip", "link", "set", interface.ifname_host, "master", self.bridge_name])
            except subprocess.CalledProcessError as err:
                raise NsNetSimError(
                    f"Failed to set master for '{interface.ifname_host}' to '{self.bridge_name}': {err.stdout}"
                ) from None

    def _remove(self):
        """Remove the namespace."""

        if self._created:
            try:
                self.run_check_call(["/usr/bin/ip", "link", "del", self.bridge_name])
            except subprocess.CalledProcessError as err:
                raise NsNetSimError(f"Failed to remove host bridge '{self.bridge_name}': {err.stdout}")
            # Flip flag to indicate that the bridge is no longer created
            self._created = False

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
