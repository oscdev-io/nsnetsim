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

"""Namespace node support."""

import os
import json
import subprocess
from typing import Any, Dict, List, Optional

from .generic_node import GenericNode
from .namespace_network_interface import NamespaceNetworkInterface
from .netns import NetNS


class NamespaceNode(GenericNode):
    """NamespaceNode implements the basic network namespace isolation we need for nodes."""

    # Name of the namespace we've created
    _namespace: str
    # Interfaces we've added to the namespace
    _interfaces: List[NamespaceNetworkInterface]
    # Create a run dir
    _rundir: str
    # Routes to add
    _routes: List[List[str]]

    def _init(self, **kwargs):
        """Initialize the object."""

        # Set the namespace name we're going to use
        self._namespace = f"ns-{self._name}"

        # Start with a clean list of interfaces
        self._interfaces = []

        # Create a directory in /run for us
        self._rundir = f"/run/nsnetsim/{self._namespace}"
        if not os.path.exists(self._rundir):
            os.makedirs(self._rundir)

        # Start with no routes
        self._routes = []

    def _create(self):
        """Create the namespace."""

        # Create namespace
        subprocess.check_call(["ip", "netns", "add", self.namespace])

        # Bring the lo interface up
        self.run(["ip", "link", "set", "lo", "up"])

        # Create interfaces
        for interface in self._interfaces:
            # Create interface
            interface.create()

        # Drop into namespace
        with NetNS(nsname=self.namespace):
            # Enable forwarding
            with open(f"/proc/sys/net/ipv4/conf/all/forwarding", "w") as forwarding_file:
                forwarding_file.write("1")
            with open(f"/proc/sys/net/ipv6/conf/all/forwarding", "w") as forwarding_file:
                forwarding_file.write("1")

        # Add routes to the namespace
        for route in self._routes:
            route_args = ["ip", "route", "add"]
            route_args.extend(route)
            res = self.run(route_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if res.returncode != 0:
                self._log(f'Failed to run in "{self.name}": {res.stdout}')

    def _remove(self):
        """Remove the namespace."""

        # Remove interfaces first
        for interface in reversed(self._interfaces):
            interface.remove()

        # Remove the namespace
        subprocess.check_call(["ip", "netns", "del", self.namespace])

    def add_interface(self, name: str, mac: Optional[str] = None) -> NamespaceNetworkInterface:
        """Add network interface to namespace."""

        # Build options
        args: Dict[str, Any] = {}
        args["name"] = name
        args["logger"] = self._logger
        args["namespace"] = self
        args["mac"] = mac

        interface = NamespaceNetworkInterface(**args)
        self._interfaces.append(interface)

        return interface

    def add_route(self, route: List[str]):
        """Add route to the namespace."""
        self._routes.append(route)

    def run(self, args, **kwargs) -> Any:
        """Run command inside the namespace."""

        # Build command to execute
        cmd_args = ["ip", "netns", "exec", self.namespace]
        cmd_args.extend(args)

        # Run command
        return subprocess.run(cmd_args, **kwargs)

    def run_ip(self, args: List[str]) -> Any:
        """Run the 'ip' tool and decode its return output."""
        # Run the IP tool with JSON output
        cmd_args = ["ip", "--json"]
        # Add our args
        cmd_args.extend(args)

        # Grab result from process execution
        result = self.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Return the decoded json output
        return json.loads(result.stdout)

    @property
    def namespace(self):
        """Return the namespace name."""
        return self._namespace

    @property
    def routes(self):
        """Return the namespace routes."""
        return self._routes
