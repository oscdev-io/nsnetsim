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
import time
from typing import Any, Dict, List, Union

from .generic_node import GenericNode
from .netns import NetNS

__version__ = "0.0.7"


class NamespaceNetworkInterface(GenericNode):
    """NamespaceInterface implements a network interface within a NamespaceNode."""

    # Namespace we're linked to
    _namespace: object
    # Name of the interfaces we've created
    _ifname_host: str
    # Interface mac address
    _mac: str
    _settings: Dict[str, Any]
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

        self._settings = {
            # Disable IPv6 DAD by default
            'ipv6_dad': kwargs.get('ipv6_dad', 0),
            # Disable IPv6 RA by default
            'ipv6_ra': kwargs.get('ipv6_ra', 0),
        }

        # Start with a clean list of IP's
        self._ip_addresses = []

    # pylama: ignore=C901,R0912
    def _create(self):
        """Create the interface."""

        # Create the interface pair
        subprocess.check_call(['ip', 'link', 'add', self.ifname_host,
                               'link-netns', self.namespace.namespace,
                               'type', 'veth', 'peer', self.ifname,
                               ])
        # Set MAC address
        res = self.namespace.run(['ip', 'link', 'set', self.ifname, 'address', self._mac], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True)
        if res.returncode != 0:
            self._log(f'Failed to set MAC address for "{self.name}" interface "{self.ifname}": {res.stdout}')

        # Disable host IPv6 DAD
        with open(f'/proc/sys/net/ipv6/conf/{self.ifname_host}/accept_dad', 'w') as ipv6_dad_file:
            ipv6_dad_file.write('0')
        # Disable host IPv6 RA
        with open(f'/proc/sys/net/ipv6/conf/{self.ifname_host}/accept_ra', 'w') as ipv6_ra_file:
            ipv6_ra_file.write('0')

        # Drop into namespace
        with NetNS(nsname=self.namespace.namespace):
            # Write out DAD value
            with open(f'/proc/sys/net/ipv6/conf/{self.ifname}/accept_dad', 'w') as ipv6_dad_file:
                ipv6_dad_file.write(f'{self.ipv6_dad}')
            # Write out RA value
            with open(f'/proc/sys/net/ipv6/conf/{self.ifname}/accept_ra', 'w') as ipv6_ra_file:
                ipv6_ra_file.write(f'{self.ipv6_ra}')

        # Add ip's to the namespace interface
        has_ipv6 = False
        for ip_address_raw in self.ip_addresses:
            args = ['ip', 'address', 'add', ip_address_raw, 'dev', self.ifname]

            ip_address = ipaddress.ip_network(ip_address_raw, strict=False)
            # Check if we need to add a broadcast address for IPv4
            if (ip_address.version == 4) and (ip_address.prefixlen < 31):
                args.extend(['broadcast', f'{ip_address.broadcast_address}'])
            if ip_address.version == 6:
                has_ipv6 = True

            # Set interface up on namespace side
            res = self.namespace.run(args)
            if res.returncode != 0:
                self._log(f'Failed to add IP address for "{self.name}" interface "{self.ifname}" IP "{ip_address_raw}": ' +
                          f'{res.stdout}')

        # Set interface up on host side
        subprocess.check_call(['ip', 'link', 'set', self.ifname_host, 'up'])
        # Set interface up on namespace side
        self.namespace.run(['ip', 'link', 'set', self.ifname, 'up'])

        # We need to wait until the interface IPv6 is up
        if has_ipv6:
            attempts = 60
            has_ll6 = False
            has_addr = False
            while attempts > 0:
                # We either need a site or global address
                if not has_addr:
                    result = self.namespace.run(
                        ['ip', '-6', '-oneline', 'address', 'show', 'dev', self.ifname, 'scope', 'site', '-tentative'],
                        stdout=subprocess.PIPE, text=True,
                    )
                    if result.stdout:
                        has_addr = True
                        continue

                    result = self.namespace.run(
                        ['ip', '-6', '-oneline', 'address', 'show', 'dev', self.ifname, 'scope', 'global', '-tentative'],
                        stdout=subprocess.PIPE, text=True,
                    )
                    if result.stdout:
                        has_addr = True

                # We need a link local address not in the tentative state
                if not has_ll6:
                    result = self.namespace.run(
                        ['ip', '-6', '-oneline', 'address', 'show', 'dev', self.ifname, 'scope', 'link', '-tentative'],
                        stdout=subprocess.PIPE, text=True,
                    )
                    if result.stdout:
                        has_ll6 = True

                # If we have both, break
                if has_ll6 and has_addr:
                    break

                # Sleep 0.1 second
                time.sleep(0.1)
                attempts = attempts - 1

            # Throw a runtime exception if we didn't manage to get a our addresses
            if attempts == 0:
                result = self.namespace.run(
                    ['ip', '-details', '-6', 'address', 'show', 'dev', self.ifname],
                    stdout=subprocess.PIPE, text=True,
                )

                raise RuntimeError(f'Failed to get IPv6 link-local address >> {result.stdout}')

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
    def ipv6_dad(self):
        """Return the interfaces IPv6 DAD attribute."""
        return self._settings['ipv6_dad']

    @property
    def ipv6_ra(self):
        """Return the interfaces IPv6 RA attribute."""
        return self._settings['ipv6_ra']

    @property
    def ip_addresses(self):
        """Return the IP addresses for the interface."""
        return self._ip_addresses
