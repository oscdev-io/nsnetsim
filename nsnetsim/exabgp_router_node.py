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

"""ExaBGP router support."""

import contextlib
import getpass
import os
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
    _exabgp_process: Optional[subprocess.CompletedProcess[str]]

    def _init(self, **kwargs: Any) -> None:
        """Initialize the object."""

        # Call parent create
        super()._init()

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
        self._exabgp_process = None

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

        # Work out the arguments we're going to pass
        # args = ["exabgp"]
        # # If we were given a config file, add it
        # if self._configfile:
        #    args.append(self._configfile)
        # Run from sh so we can get the console output
        args = ["sh", "-c", f"exabgp --debug {self._configfile} >> {self._logfile} 2>&1"]

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

        # Fork ExaBGP into the background for statup
        # NK: in some odd situations it seems to of hung during startup, so we're going to run it in a forked process so we can
        # catch any output to console
        pid = os.fork()
        if pid == 0:
            # Run ExaBGP within the network namespace
            try:
                self.run_in_ns_check_call(args, env=environment)
            except subprocess.CalledProcessError as err:
                raise NsNetSimError(f"Failed to start ExaBGP with configuration file '{self._configfile}': {err.stdout}") from None
            # Exit child process using os._exit to bypass pytest SystemExit exception
            os._exit(0)
        elif pid < 0:
            raise NsNetSimError("Failed to fork ExaBGP process")

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
                self._log_warning(f"Failed to kill ExaBGP process PID {pid}")
            # Remove pid file
            with contextlib.suppress(FileNotFoundError):
                os.remove(self._pidfile)

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
