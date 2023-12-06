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

"""BIRD router support."""

import contextlib
import os
import signal
import subprocess  # nosec
from typing import Any, Dict, List

from birdclient import BirdClient, BirdClientError

from .exceptions import NsNetSimError
from .router_node import RouterNode

__all__ = ["BirdRouterNode"]


class BirdRouterNode(RouterNode):
    """BirdRouterNode implements a network isolated BIRD router node."""

    # Configuration file
    _configfile: str
    # Control socket
    _controlsocket: str
    # PID file
    _pidfile: str

    def _init(self, **kwargs: Any) -> None:
        """Initialize the object."""

        # Call parent create
        super()._init()

        # We should be getting a config file
        configfile = kwargs.get("configfile")
        if not configfile:  # pragma: no cover
            raise NsNetSimError('The "configfile" argument should of been provided')
        # Check it exists
        if not os.path.exists(configfile):  # pragma: no cover
            raise NsNetSimError(f'BIRD config file "{configfile}" does not exist')
        # Set config file
        self._configfile = configfile

        # Set control socket
        self._controlsocket = f"{self._rundir}/bird-control.socket"
        self._pidfile = f"{self._rundir}/bird.pid"

        # Test config file
        try:
            self.run_check_call(["/usr/bin/bird", "-c", self._configfile, "-p"])  # nosec
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to validate BIRD config file '{self._configfile}': {err.stdout}") from None

    # Send something to birdc
    def birdc(self, query: str) -> List[str]:
        """Send a query to birdc."""
        try:
            res: List[str] = self._birdc.query(query)
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_status(self) -> Dict[str, str]:
        """Return status."""
        try:
            res: Dict[str, str] = self._birdc.show_status()
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_protocol(self, protocol: str) -> Dict[str, Any]:
        """Return protocol."""
        try:
            res: Dict[str, Any] = self._birdc.show_protocol(protocol)
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_protocols(self) -> Dict[str, Any]:
        """Return protocols."""
        try:
            res: Dict[str, Any] = self._birdc.show_protocols()
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_route_table(self, table: str) -> Dict[Any, Any]:
        """
        Return a BIRD routing table.

        Parameters
        ----------
        table : str
            Routing table to retrieve.

        """

        res: Dict[Any, Any] = self._birdc.show_route_table(table)

        return res

    @property
    def _birdc(self) -> BirdClient:
        """Return BirdClient instance."""
        return BirdClient(self._controlsocket, debug=self._debug)

    def _create(self) -> None:
        """Create the router."""

        # Call parent create
        super()._create()

        # Run bird within the network namespace
        try:
            self.run_in_ns_check_call(["/usr/bin/bird", "-c", self._configfile, "-s", self._controlsocket, "-P", self._pidfile])
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to start BIRD with configuration file '{self._configfile}': {err.stdout}") from None

    def _remove(self) -> None:
        """Remove the router."""

        # Grab PID of the process...
        if os.path.exists(self._pidfile):
            try:
                with open(self._pidfile, "r", encoding="UTF-8") as pidfile_file:
                    pid = int(pidfile_file.read())
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to open PID file '{self._pidfile}' for writing: {err}") from None
            # Terminate process
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:  # pragma: no cover
                self._log_warning(f"Failed to kill BIRD process PID {pid}")
            # Remove pid file
            with contextlib.suppress(FileNotFoundError):
                os.remove(self._pidfile)

        # Call parent remove
        super()._remove()
