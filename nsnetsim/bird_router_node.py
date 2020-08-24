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

"""BIRD router support."""

import os
import signal
import subprocess  # nosec
import time
from typing import Any, Dict, List, Optional

from birdclient import BirdClient, BirdClientError
from .exceptions import NsNetSimError
from .router_node import RouterNode


class BirdRouterNode(RouterNode):
    """BirdRouterNode implements a network isolated BIRD router node."""

    # Configuration file
    _configfile: str
    # Control socket
    _controlsocket: str
    # PID file
    _pidfile: str

    def _init(self, **kwargs):
        """Initialize the object."""

        # Call parent create
        super()._init()

        # We should be getting a config file
        configfile = kwargs.get("configfile", None)
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

        # We start out with no process
        self._bird_process = None

    # Send something to birdc
    def birdc(self, query: str) -> List[str]:
        """Send a query to birdc."""
        birdc = BirdClient(self._controlsocket)
        try:
            return birdc.query(query)
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err

    def birdc_show_status(self) -> Dict[str, str]:
        """Return status."""
        birdc = BirdClient(self._controlsocket)
        try:
            return birdc.show_status()
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err

    def birdc_show_protocols(self) -> Dict[str, Any]:
        """Return protocols."""
        birdc = BirdClient(self._controlsocket)
        try:
            return birdc.show_protocols()
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err

    def birdc_show_route_table(  # pylint:disable=C0330
        self, table: str, expect_count: Optional[int] = None, expect_content: Optional[str] = None, expect_timeout: int = 30
    ) -> List:
        """
        Return a routing table, optionally trying to wait for an expected count of entries and optional timeout.

        Parameters
        ----------
        table : str
            Routing table to retrieve.
        expect_count : Optional[int]
            Optional number of entries we expect, we will wait for `expect_timeout` seconds before giving up.
        expect_content : Optional[str]
            Optional string representation of the routing table to match against, we will wait for `expect_timeout` seconds before
            giving up.
        expect_timeout : int
            Optional amount of time to wait to get `expect_count` entries, defaults to 30 (seconds).

        """

        birdc = BirdClient(self._controlsocket)

        # Save the start time
        time_start = time.time()

        # Start with a blank result
        result = []
        while True:
            # Try get a result from birdc
            try:
                result = birdc.show_route_table(table)
            except BirdClientError as err:  # pragma: no cover
                raise NsNetSimError(f"{err}") from err

            count_matches = False
            content_matches = False

            # If we're not expecting a count of table entries, we match
            if not expect_count:
                count_matches = True
            # If we are expecting a count, check to see if we have the number we need
            elif len(result) >= expect_count:
                count_matches = True

            # If we don't have a content match, we match
            if not expect_content:
                content_matches = True
            # Else check that the result contains the content we're looking for
            else:
                result_str = f"{result}"
                if expect_content in result_str:
                    content_matches = True

            # Check if have what we expected
            if count_matches and content_matches:
                break

            # If not, check to see if we've exceeded our timeout
            if time.time() - time_start > expect_timeout:
                break

            time.sleep(0.5)

        return result

    def _create(self):
        """Create the router."""

        # Call parent create
        super()._create()

        # Run bird within the network namespace
        try:
            self.run_in_ns_check_call(["/usr/bin/bird", "-c", self._configfile, "-s", self._controlsocket, "-P", self._pidfile])
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to start BIRD with configuration file '{self._configfile}': {err.stdout}") from None

    def _remove(self):
        """Remove the router."""

        # Grab PID of the process...
        if os.path.exists(self._pidfile):
            try:
                with open(self._pidfile, "r") as pidfile_file:
                    pid = int(pidfile_file.read())
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to open PID file '{self._pidfile}' for writing: {err}")
            # Terminate process
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:  # pragma: no cover
                self._log_warning(f"Failed to kill BIRD process PID {pid}")
            # Remove pid file
            try:
                os.remove(self._pidfile)
            except FileNotFoundError:  # pragma: no cover
                pass

        # Call parent remove
        super()._remove()
