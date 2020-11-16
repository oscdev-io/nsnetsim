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

"""Network interface support within a namespace node."""

import ipaddress
import random
import secrets
import subprocess  # nosec
import time
from typing import Any, Dict, List, Union, TYPE_CHECKING
from .exceptions import NsNetSimError
from .generic_node import GenericNode
from .netns import NetNS

if TYPE_CHECKING:  # pragma: no cover
    from .namespace_node import NamespaceNode


class NamespaceNetworkInterface(GenericNode):
    """NamespaceInterface implements a network interface within a NamespaceNode."""

    # Namespace we're linked to
    _namespace_node: "NamespaceNode"
    # Name of the interfaces we've created
    _ifname_host: str
    # Interface mac address
    _mac: str
    _settings: Dict[str, Any]
    # IP's for interface
    _ip_addresses: List[str]
    # Indication if the interface was created
    _created: bool

    def _init(self, **kwargs):
        """Initialize the object."""

        # Make sure we have an namespace
        self._namespace_node = kwargs.get("namespace_node", None)
        if not self._namespace_node:  # pragma: no cover
            raise NsNetSimError('The argument "namespace_node" should of been specified')

        # Set the namespace name we're going to use
        self._ifname_host = f"veth-{secrets.token_hex(4)}"

        # Add some extra logging info
        self._extra_log = f' in "{self.namespace_node.name}"'

        # Assign an interface mac address
        self._mac = kwargs.get("mac", None)
        if not self._mac:
            self._mac = "02:%02x:%02x:%02x:%02x:%02x" % (
                random.randint(0, 255),  # nosec
                random.randint(0, 255),  # nosec
                random.randint(0, 255),  # nosec
                random.randint(0, 255),  # nosec
                random.randint(0, 255),  # nosec
            )

        self._settings = {
            # Disable IPv6 DAD by default
            "ipv6_dad": kwargs.get("ipv6_dad", 0),
            # Disable IPv6 RA by default
            "ipv6_ra": kwargs.get("ipv6_ra", 0),
        }

        # Start with a clean list of IP's
        self._ip_addresses = []

        # Indicate the interface has not yet been created
        self._created = False

    # pylama: ignore=C901,R0912
    def _create(self):
        """Create the interface."""

        # Create the interface pair
        retry = 5
        error = ""
        while retry > 0:
            try:
                self.run_check_call(
                    [
                        "/usr/bin/ip",
                        "link",
                        "add",
                        self.ifname_host,
                        "link-netns",
                        self.namespace_node.namespace,
                        "type",
                        "veth",
                        "peer",
                        self.ifname,
                    ]
                )
                break

            except subprocess.CalledProcessError as err:  # pragma: no cover
                error = f"{err.stdout}"
                time.sleep(1)

            # Reduce retry counter
            retry -= 1

        if not retry and error:
            raise NsNetSimError(
                f"Failed to create veth {self.ifname_host} => {self.ifname} [{self.namespace_node.namespace}]: {error}"
            )

        # Indicate the interface has been created
        self._created = True

        # Set MAC address
        try:
            self.namespace_node.run_in_ns_check_call(["/usr/bin/ip", "link", "set", self.ifname, "address", self._mac])
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f'Failed to set MAC address for "{self.name}" interface "{self.ifname}": {err.stdout}') from None

        # Disable host IPv6 DAD
        try:
            with open(f"/proc/sys/net/ipv6/conf/{self.ifname_host}/accept_dad", "w") as ipv6_dad_file:
                ipv6_dad_file.write("0")
        except OSError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to set host 'accept_dad' to 0: {err}") from None
        # Disable host IPv6 RA
        try:
            with open(f"/proc/sys/net/ipv6/conf/{self.ifname_host}/accept_ra", "w") as ipv6_ra_file:
                ipv6_ra_file.write("0")
        except OSError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to set host 'accept_ra' to 0: {err}") from None

        # Drop into namespace
        with NetNS(nsname=self.namespace_node.namespace):
            # Disable namespace IPv6 DAD
            try:
                with open(f"/proc/sys/net/ipv6/conf/{self.ifname}/accept_dad", "w") as ipv6_dad_file:
                    ipv6_dad_file.write(f"{self.ipv6_dad}")
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to set namespace 'accept_dad' to 0: {err}") from None
            # Disable namespace IPv6 RA
            try:
                with open(f"/proc/sys/net/ipv6/conf/{self.ifname}/accept_ra", "w") as ipv6_ra_file:
                    ipv6_ra_file.write(f"{self.ipv6_ra}")
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to set namespace 'accept_dad' to 0: {err}") from None

        # Add ip's to the namespace interface
        has_ipv6 = False
        for ip_address_raw in self.ip_addresses:
            args = ["/usr/bin/ip", "address", "add", ip_address_raw, "dev", self.ifname]

            ip_address = ipaddress.ip_network(ip_address_raw, strict=False)
            # Check if we need to add a broadcast address for IPv4
            if (ip_address.version == 4) and (ip_address.prefixlen < 31):
                args.extend(["broadcast", f"{ip_address.broadcast_address}"])
            if ip_address.version == 6:
                has_ipv6 = True

            # Set interface up on namespace side
            try:
                self.namespace_node.run_in_ns_check_call(args)
            except subprocess.CalledProcessError as err:  # pragma: no cover
                raise NsNetSimError(
                    f"Failed to add IP address for '{self.name}'' interface '{self.ifname}' IP '{ip_address_raw}': {err.stdout}"
                ) from None

        # Set interface up on host side
        try:
            self.run_check_call(["/usr/bin/ip", "link", "set", self.ifname_host, "up"])
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to set host interface '{self.ifname_host}' up: {err.stdout}") from None
        # Set interface up on namespace side
        try:
            self.namespace_node.run_in_ns_check_call(["/usr/bin/ip", "link", "set", self.ifname, "up"])
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to set namespace interface '{self.ifname}' up: {err.stdout}") from None

        # We need to wait until the interface IPv6 is up
        if has_ipv6:
            attempts = 60
            has_ll6 = False
            has_addr = False
            while attempts > 0:
                # We either need a site or global address
                if not has_addr:
                    try:
                        result = self.namespace_node.run_in_ns_check_output(
                            ["/usr/bin/ip", "-6", "-oneline", "address", "show", "dev", self.ifname, "scope", "site", "-tentative"],
                        )
                    except subprocess.CalledProcessError as err:  # pragma: no cover
                        raise NsNetSimError(f"Failed to get site scoped tentative addresses: {err.stderr}") from None
                    # Check if we have output
                    if result.stdout:  # pragma: no cover
                        has_addr = True
                        continue

                    try:
                        result = self.namespace_node.run_in_ns_check_output(
                            [
                                "/usr/bin/ip",
                                "-6",
                                "-oneline",
                                "address",
                                "show",
                                "dev",
                                self.ifname,
                                "scope",
                                "global",
                                "-tentative",
                            ],
                        )
                    except subprocess.CalledProcessError as err:  # pragma: no cover
                        raise NsNetSimError(f"Failed to get global scoped tentative addresses: {err.stderr}") from None
                    # Check if we have output
                    if result.stdout:
                        has_addr = True

                # We need a link local address not in the tentative state
                if not has_ll6:
                    try:
                        result = self.namespace_node.run_in_ns_check_output(
                            ["/usr/bin/ip", "-6", "-oneline", "address", "show", "dev", self.ifname, "scope", "link", "-tentative"]
                        )
                    except subprocess.CalledProcessError as err:  # pragma: no cover
                        raise NsNetSimError(f"Failed to get link scoped tentative addresses: {err.stderr}") from None
                    # Check if we have output
                    if result.stdout:  # pragma: no cover
                        has_ll6 = True

                # If we have both, break
                if has_ll6 and has_addr:  # pragma: no cover
                    break

                # Sleep 0.1 second
                time.sleep(0.1)  # pragma: no cover
                attempts = attempts - 1  # pragma: no cover

            # Throw a runtime exception if we didn't manage to get a our addresses
            if attempts == 0:  # pragma: no cover
                try:
                    result = self.namespace_node.run_in_ns_check_call(
                        ["/usr/bin/ip", "-details", "-6", "address", "show", "dev", self.ifname]
                    )
                except subprocess.CalledProcessError as err:
                    raise NsNetSimError(
                        f"Failed to get IPv6 adresses in namespace '{self.namespace_node.namespace}': {err.stdout}"
                    ) from None

                raise NsNetSimError(
                    f"Failed to get IPv6 link-local address in namespace '{self.namespace_node.namespace}': {result.stdout}"
                )

    def _remove(self):
        """Remove the interface."""

        # Remove the interface
        if self._created:
            try:
                self.run_check_call(["/usr/bin/ip", "link", "del", self.ifname_host])
            except subprocess.CalledProcessError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to remove veth '{self.ifname_host}' from host: {err.stdout}") from None
            # Indicate that the interface is no longer created
            self._created = False

    def add_ip(self, ip_address: Union[str, list]):
        """Add IP to the namespace interface."""
        if isinstance(ip_address, list):
            self._ip_addresses.extend(ip_address)
        else:
            self._ip_addresses.append(ip_address)

    @property
    def namespace_node(self):
        """Return the namespace we're linked to."""
        return self._namespace_node

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
        return self._settings["ipv6_dad"]

    @property
    def ipv6_ra(self):
        """Return the interfaces IPv6 RA attribute."""
        return self._settings["ipv6_ra"]

    @property
    def ip_addresses(self):
        """Return the IP addresses for the interface."""
        return self._ip_addresses
