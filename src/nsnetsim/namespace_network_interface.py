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

"""Network interface support within a namespace node."""

import ipaddress
import random
import subprocess
from typing import List, Union

from .generic_node import GenericNode
from .netns import NetNS

__version__ = "0.0.1"


class NamespaceNetworkInterface(GenericNode):
    """NamespaceInterface implements a network interface within a NamespaceNode."""

    # Namespace we're linked to
    _namespace: object
    # Name of the interfaces we've created
    _ifname_host: str
    # Interface mac address
    _mac: str
    # Fowarding
    _forwarding: int
    # IP's for interface
    _ip_addresses: List[str]

    def _init(self, **kwargs):
        """Initialize the object."""

        # Make sure we have an namespace
        self._namespace = kwargs.get('namespace', None)
        if not self._namespace:
            raise RuntimeError('The argument "namespace" should of been specified')

        # Set the namespace name we're going to use
        self._ifname_host = f'{self.namespace.name}-{self.name}'

        # Add some extra logging info
        self._extra_log = f' in "{self.namespace.name}"'

        # Assign an interface mac address
        self._mac = kwargs.get('mac', None)
        if not self._mac:
            self._mac = "02:%02x:%02x:%02x:%02x:%02x" % (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            )

        # Enable forwarding by default
        self._forwarding = kwargs.get('forwarding', 1)

        # Start with a clean list of IP's
        self._ip_addresses = []

    def _create(self):
        """Create the interface."""

        # Create the interface pair
        subprocess.check_call(['ip', 'link', 'add', self.ifname_host,
                               'link-netns', self.namespace.namespace,
                               'type', 'veth', 'peer', self.ifname,
                               ])
        # Set MAC address
        self.namespace.run(['ip', 'link', 'set', self.ifname, 'address', self._mac])
        # Set interface up on host side
        subprocess.check_call(['ip', 'link', 'set', self.ifname_host, 'up'])
        # Set interface up on namespace side
        self.namespace.run(['ip', 'link', 'set', self.ifname, 'up'])

        # Add ip's to the namespace interface
        for ip_address_raw in self.ip_addresses:
            args = ['ip', 'address', 'add', ip_address_raw, 'dev', self.ifname]

            # We need to add a broadcast address for IPv4
            ip_address = ipaddress.ip_network(ip_address_raw, strict=False)
            if ip_address.version == 4:
                args.extend(['broadcast', f'{ip_address.broadcast_address}'])

            # Set interface up on namespace side
            self.namespace.run(args)

        # If we're doing fowarding
        if self._forwarding:
            # Drop into namespace
            with NetNS(nsname=self.namespace.namespace):
                # Write out fowarding value
                with open(f'/proc/sys/net/ipv4/conf/{self.ifname}/forwarding', 'w') as forwarding_file:
                    forwarding_file.write(f'{self.forwarding}')
                with open(f'/proc/sys/net/ipv6/conf/{self.ifname}/forwarding', 'w') as forwarding_file:
                    forwarding_file.write(f'{self.forwarding}')

    def _remove(self):
        """Remove the interface."""

        # Remove the interface
        subprocess.check_call(['ip', 'link', 'del', self.ifname_host])

    def add_ip(self, ip_address: Union[str, list]):
        """Add IP to the namespace interface."""
        if isinstance(ip_address, list):
            self._ip_addresses.extend(ip_address)
        else:
            self._ip_addresses.append(ip_address)

    @property
    def namespace(self):
        """Return the namespace we're linked to."""
        return self._namespace

    @property
    def ifname(self):
        """Return the namespace-side interface name."""
        return self._name

    @property
    def ifname_host(self):
        """Return the host-side interface name."""
        return self._ifname_host

    @property
    def forwarding(self):
        """Return the interfaces forwarding attribute."""
        return self._forwarding

    @property
    def ip_addresses(self):
        """Return the IP addresses for the interface."""
        return self._ip_addresses
