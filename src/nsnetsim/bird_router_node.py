#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2019-2024, AllWorldIT.
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
import pathlib
import shutil
import signal
import subprocess  # nosec
from typing import Any

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

    def _init(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the object."""
        # Call parent create
        super()._init()

        # Make sure bird path is returned by which
        if not shutil.which("bird"):
            raise NsNetSimError("Bird binary not found in PATH")

        # We should be getting a config file
        configfile = kwargs.get("configfile")
        if not configfile:  # pragma: no cover
            raise NsNetSimError('The "configfile" argument should of been provided')
        # Check it exists
        configfile_path = pathlib.Path(configfile)
        if not configfile_path.exists():  # pragma: no cover
            raise NsNetSimError(f'BIRD config file "{configfile}" does not exist')
        # Set config file
        self._configfile = configfile

        # Set control socket
        controlsocket = kwargs.get("controlsocket")
        if not controlsocket:
            controlsocket = f"{self._rundir}/bird.ctl"
        self._controlsocket = controlsocket

        self._pidfile = f"{self._rundir}/bird.pid"

        # Test config file
        try:
            res = self.run_check_call(["bird", "-c", self._configfile, "-p"])  # nosec
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to validate BIRD config file '{self._configfile}': {err.stdout}") from None
        # Look for errors in output
        if "error" in res.stdout:
            raise NsNetSimError(f"Failed to validate BIRD config file '{self._configfile}': {res.stdout}") from None

    # Send something to birdc
    def birdc(self, query: str) -> list[str]:
        """Send a query to birdc."""
        try:
            res: list[str] = self._birdc.query(query)
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_status(self) -> dict[str, str]:
        """Return status."""
        try:
            res: dict[str, str] = self._birdc.show_status()
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_protocol(self, protocol: str) -> dict[str, Any]:
        """Return protocol."""
        try:
            res: dict[str, Any] = self._birdc.show_protocol(protocol)
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_protocols(self) -> dict[str, Any]:
        """Return protocols."""
        try:
            res: dict[str, Any] = self._birdc.show_protocols()
        except BirdClientError as err:  # pragma: no cover
            raise NsNetSimError(f"{err}") from err
        return res

    def birdc_show_route_table(self, table: str) -> dict[Any, Any]:
        """
        Return a BIRD routing table.

        Parameters
        ----------
        table : str
            Routing table to retrieve.

        """

        res: dict[Any, Any] = self._birdc.show_route_table(table)

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
            self.run_in_ns_check_call(["bird", "-c", self._configfile, "-s", self._controlsocket, "-P", self._pidfile])
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to start BIRD with configuration file '{self._configfile}': {err.stdout}") from None

    def _remove(self) -> None:
        """Remove the router."""

        # Grab PID of the process...
        pidfile_path = pathlib.Path(self._pidfile)
        if pidfile_path.exists():
            try:
                with pidfile_path.open(encoding="UTF-8") as pidfile_file:
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
                pidfile_path.unlink()

        # Call parent remove
        super()._remove()
