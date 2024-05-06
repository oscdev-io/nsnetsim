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

"""ExaBGP router support."""

import getpass
import os
import shutil
import signal
import subprocess  # nosec
from typing import Any, List, Optional

from .exceptions import NsNetSimError
from .router_node import RouterNode

__all__ = ["ExaBGPRouterNode"]


class ExaBGPRouterNode(RouterNode):
    """ExaBGPRouterNode implements a network isolated ExaBGP router node."""

    # Configuration file
    _configfile: str
    # Control socket
    _namedpipe: str
    # PID file
    _pidfile: str
    # Pipes
    _fifo_in: str
    _fifo_out: str
    # Log file
    _logfile: str
    # ExaBGP process
    _process: Optional[subprocess.Popen]

    def _init(self, **kwargs: Any) -> None:
        """Initialize the object."""
        # Call parent create
        super()._init()

        # Make sure exabgp path is returned by which
        if not shutil.which("exabgp"):
            raise NsNetSimError("ExaBGP binary not found in PATH")

        # We should be getting a config file
        configfile = kwargs.get("configfile")
        # Check we have a config file
        if not configfile:
            raise NsNetSimError("ExaBGP config file not provided")
        # Check it exists
        if not os.path.exists(configfile):  # pragma: no cover
            raise NsNetSimError(f'ExaBGP config file "{configfile}" does not exist')
        # Set config file
        self._configfile = configfile

        # Set named pipe
        name = f"exabgp-{self._name}"
        self._namedpipe = f"exabgp-{self.namespace}"
        self._pidfile = f"{self._rundir}/{name}.pid"
        self._fifo_in = f"/run/{self._namedpipe}.in"
        self._fifo_out = f"/run/{self._namedpipe}.out"
        self._logfile = f"{self._rundir}/{name}.log"

        # Test config file
        try:
            self.run_check_call(["exabgp", "--test", self._configfile])  # nosec
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to validate ExaBGP config file '{self._configfile}': {err.stdout}") from None

        # We start out with no process
        self._process = None

    def exabgpcli(self, args: List[str]) -> List[str]:
        """Send a query to ExaBGP."""

        cmdline = ["exabgpcli"]
        cmdline.extend(args)

        # Now for the actual configuration, which is done using the environment
        environment = {
            "exabgp.api.pipename": self._namedpipe,
        }

        try:
            res = self.run_in_ns_check_output(cmdline, env=environment)
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to run ExaBGP command {cmdline}: {err.stderr}") from None

        ret: List[str] = res.stdout.splitlines()

        return ret

    def _create(self) -> None:
        """Create the router."""

        # Call parent create
        super()._create()

        args = ["exabgp", "--debug", self._configfile]

        # Now for the actual configuration, which is done using the environment
        environment = {
            "exabgp.api.pipename": self._namedpipe,
            # NK: We will start it in the foreground in its own process below so we can continue with the other nodes to link the
            # interface to the switch. This means we will not daemonize it here.
            # "exabgp.daemon.daemonize": "true",
            "exabgp.daemon.pid": self._pidfile,
            "exabgp.daemon.user": getpass.getuser(),
            "exabgp.log.all": "true",
            "exabgp.log.destination": self._logfile,
        }

        # Create fifos for exabgpcli
        try:
            os.mkfifo(self._fifo_in)
        except OSError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to create ExaBGP fifo file '{self._fifo_in}': {err}") from None
        try:
            os.mkfifo(self._fifo_out)
        except OSError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to create ExaBGP fifo file '{self._fifo_out}': {err}") from None

        # Start StayRTR process using subprocess.Popen
        logfile_f = open(self._logfile, "w", encoding="UTF-8")  # pylint: disable=consider-using-with
        self._process = self.run_in_ns_popen(args, env=environment, stdout=logfile_f, stderr=subprocess.STDOUT)

    def _remove(self) -> None:
        """Remove the router."""

        # Kill process
        if self._process:
            # Try terminate
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            # If that doesn't work, force kill the entire group
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)

        # Remove fifo's
        if os.path.exists(self._fifo_in):
            os.remove(self._fifo_in)
        if os.path.exists(self._fifo_out):
            os.remove(self._fifo_out)

        # Call parent remove
        super()._remove()

    @property
    def logfile(self) -> str:
        """Return our log file."""
        return self._logfile
