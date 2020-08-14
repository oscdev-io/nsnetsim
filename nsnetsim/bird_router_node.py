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

"""BIRD router support."""

import os
import signal
import subprocess
from typing import Any, Dict, List

from birdclient import BirdClient
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
        if not configfile:
            raise RuntimeError('The "configfile" argument should of been provided')
        # Check it exists
        if not os.path.exists(configfile):
            raise RuntimeError(f'BIRD config file "{configfile}" does not exist')
        # Set config file
        self._configfile = configfile

        # Set control socket
        self._controlsocket = f"{self._rundir}/bird-control.socket"
        self._pidfile = f"{self._rundir}/bird.pid"

        # Test config file
        try:
            subprocess.check_output(["bird", "-c", self._configfile, "-p"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exception:
            output = exception.output.decode("utf-8").rstrip()
            self._log(f'ERROR: Failed to validate BIRD configuration file "{self._configfile}": ' f"{output}")
            exit(1)

        # We start out with no process
        self._bird_process = None

    # Send something to birdc
    def birdc(self, query: str) -> List[str]:
        """Send a query to birdc."""
        birdc = BirdClient(self._controlsocket)
        return birdc.query(query)

    def birdc_show_status(self) -> Dict[str, str]:
        """Return status."""
        birdc = BirdClient(self._controlsocket)
        return birdc.show_status()

    def birdc_show_protocols(self) -> Dict[str, Any]:
        """Return protocols."""
        birdc = BirdClient(self._controlsocket)
        return birdc.show_protocols()

    def birdc_show_route_table(self, table: str) -> List:
        """Return a routing table."""
        birdc = BirdClient(self._controlsocket)
        return birdc.show_route_table(table)

    def _create(self):
        """Create the router."""

        # Call parent create
        super()._create()

        # Run bird within the network namespace
        try:
            subprocess.check_output(
                [
                    "ip",
                    "netns",
                    "exec",
                    self.namespace,
                    "bird",
                    "-c",
                    self._configfile,
                    "-s",
                    self._controlsocket,
                    "-P",
                    self._pidfile,
                ]
            )
        except subprocess.CalledProcessError as exception:
            output = exception.output.decode("utf-8").rstrip()
            self._log(f'ERROR: Failed to start BIRD with configuration file "{self._configfile}": ' f"{output}")
            exit(1)

    def _remove(self):
        """Remove the router."""

        # Grab PID of the process...
        if os.path.exists(self._pidfile):
            with open(self._pidfile, "r") as pidfile_file:
                pid = int(pidfile_file.read())
            # Terminate process
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                self._log(f"WARNING: Failed to kill BIRD process {pid}")
            # Remove pid file
            try:
                os.remove(self._pidfile)
            except FileNotFoundError:
                pass

        # Call parent remove
        super()._remove()
