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

"""Namespace node support."""

import os
import json
import subprocess  # nosec
from typing import Any, Dict, List, Optional, Union

from .exceptions import NsNetSimError
from .generic_node import GenericNode
from .namespace_network_interface import NamespaceNetworkInterface
from .netns import NetNS


class NamespaceNode(GenericNode):
    """NamespaceNode implements the basic network namespace isolation we need for nodes."""

    # Name of the namespace we've created
    _namespace: str
    # Interfaces we've added to the namespace
    _interfaces: Dict[str, NamespaceNetworkInterface]
    # Create a run dir
    _rundir: str
    # Routes to add
    _routes: List[List[str]]
    # Indication the namespace was created
    _created: bool

    def _init(self, **kwargs):
        """Initialize the object."""

        # Set the namespace name we're going to use
        self._namespace = f"ns-{self.name}"

        # Start with a clean list of interfaces
        self._interfaces = {}

        # Create a directory in /run for us
        self._rundir = f"/run/nsnetsim/{self._namespace}"
        if not os.path.exists(self._rundir):
            try:
                os.makedirs(self._rundir)
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to create run directory '{self._rundir}': {err}") from None

        # Indicate the namespace has not been created yet
        self._created = False

        # Start with no routes
        self._routes = []

    def _create(self):
        """Create the namespace."""

        # Create namespace
        try:
            self.run_check_call(["/usr/bin/ip", "netns", "add", self.namespace])  # nosec
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to add network namespace '{self.namespace}': {err.stdout}") from None
        self._created = True

        # Bring the lo interface up
        try:
            self.run_in_ns_check_call(["/usr/bin/ip", "link", "set", "lo", "up"])
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to bring device 'lo' up in namespace '{self.namespace}': {err.stdout}") from None

        # Create interfaces
        for _, interface in self._interfaces.items():
            # Create interface
            interface.create()

        # Drop into namespace
        with NetNS(nsname=self.namespace):
            # Enable forwarding
            try:
                with open("/proc/sys/net/ipv4/conf/all/forwarding", "w") as forwarding_file:
                    forwarding_file.write("1")
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to enable IPv4 forwarding in network namespace '{self.namespace}': {err}") from None
            try:
                with open("/proc/sys/net/ipv6/conf/all/forwarding", "w") as forwarding_file:
                    forwarding_file.write("1")
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to enable IPv6 forwarding in network namespace '{self.namespace}': {err}") from None

        # Add routes to the namespace
        for route in self._routes:
            route_args = ["/usr/bin/ip", "route", "add"]
            route_args.extend(route)
            try:
                self.run_in_ns_check_call(route_args)
            except subprocess.CalledProcessError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to add route '{route}' to namespace '{self.namespace}': {err.stdout}") from None

    def _remove(self):
        """Remove the namespace."""

        # Remove interfaces first
        for _, interface in self._interfaces.items():
            interface.remove()

        # Remove the namespace
        if self._created:
            try:
                self.run_check_call(["/usr/bin/ip", "netns", "del", self.namespace])
            except subprocess.CalledProcessError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to remove network namespace '{self.namespace}': {err.stdout}") from None
            # Flip flag to indicate that the namespace is no longer created
            self._created = False

    def add_interface(self, name: str, mac: Optional[str] = None, ips: Optional[Union[str, list]] = None):
        """
        Add network interface to namespace.

        Parameters
        ----------
        name : str
            Name of interface to add. eg. eth0.
        mac : Optional[str]
            Optional MAC address to add, else it will be randomly generated.
        ips : Optional[Union[str, list]]
            Optinal IP's to add to the interface, either one, or a list of many.

        """

        # Check we don't have an interface with this name already
        if name in self._interfaces:
            raise NsNetSimError(f"Interface name '{name}' already exists'")

        # Create interface
        interface = NamespaceNetworkInterface(name=name, namespace_node=self, mac=mac)

        # Add to our internal structure
        self._interfaces[name] = interface

        # If we have IP's, add them too
        if ips:
            interface.add_ip(ips)

    def interface(self, name: str) -> Optional[NamespaceNetworkInterface]:
        """
        Return an interface with a specific name.

        If the interface cannot be found `None` is returned.
        """

        # If we have the interface with this name, return it
        if name in self._interfaces:
            return self._interfaces[name]

        # Else return None
        return None

    def add_route(self, route: List[str]):
        """Add route to the namespace."""
        self._routes.append(route)

    def run_in_ns_check_call(self, args, **kwargs) -> Any:
        """Run command inside the namespace similar to check_call."""
        return self._run_in_ns(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kwargs)

    def run_in_ns_check_output(self, args, **kwargs) -> Any:
        """Run command inside the namespace similar to check_call."""
        return self._run_in_ns(args, capture_output=True, text=True, **kwargs)

    def run_ip(self, args: List[str]) -> Any:
        """Run the 'ip' tool and decode its return output."""
        # Run the IP tool with JSON output
        cmd_args = ["/usr/bin/ip", "--json"]
        # Add our args
        cmd_args.extend(args)

        # Grab result from process execution
        result = self._run_in_ns(cmd_args, capture_output=True)

        # Return the decoded json output if we got something back
        if result.stdout:
            return json.loads(result.stdout)

        return None

    def _run_in_ns(self, args, **kwargs) -> Any:
        """Run command inside the namespace."""

        # Build command to execute
        cmd_args = ["/usr/bin/ip", "netns", "exec", self.namespace]
        cmd_args.extend(args)

        # Run command
        return subprocess.run(cmd_args, check=True, **kwargs)  # nosec

    @property
    def namespace(self):
        """Return the namespace name."""
        return self._namespace

    @property
    def routes(self):
        """Return the namespace routes."""
        return self._routes
