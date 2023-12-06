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

import getpass
import os
import signal
import subprocess  # nosec
from typing import List, Optional

from .exceptions import NsNetSimError
from .router_node import RouterNode


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
    _exabgp_process: Optional[subprocess.CompletedProcess]

    def _init(self, **kwargs):
        """Initialize the object."""

        # Call parent create
        super()._init()

        # We should be getting a config file
        configfile = kwargs.get("configfile", None)
        # Check it exists
        if configfile and (not os.path.exists(configfile)):  # pragma: no cover
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
            self.run_check_call(["/usr/bin/exabgp", "--test", self._configfile])  # nosec
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to validate ExaBGP config file '{self._configfile}': {err.stdout}") from None

        # We start out with no process
        self._exabgp_process = None

    def exabgpcli(self, args: List[str]) -> List[str]:
        """Send a query to ExaBGP."""

        cmdline = ["/usr/bin/exabgpcli"]
        cmdline.extend(args)

        # Now for the actual configuration, which is done using the environment
        environment = {}
        environment["exabgp.api.pipename"] = self._namedpipe

        try:
            res = self.run_in_ns_check_output(cmdline, env=environment)
        except subprocess.CalledProcessError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to run ExaBGP command {cmdline}: {err.stderr}") from None

        return res.stdout.splitlines()

    def _create(self):
        """Create the router."""

        # Call parent create
        super()._create()

        # Work out the arguments we're going to pass
        args = ["/usr/bin/exabgp"]
        # If we were given a config file, add it
        if self._configfile:
            args.append(self._configfile)

        # Now for the actual configuration, which is done using the environment
        environment = {}
        environment["exabgp.api.pipename"] = self._namedpipe
        environment["exabgp.daemon.daemonize"] = "true"
        environment["exabgp.daemon.pid"] = self._pidfile
        environment["exabgp.daemon.user"] = getpass.getuser()
        environment["exabgp.log.all"] = "true"
        environment["exabgp.log.destination"] = self._logfile

        try:
            os.mkfifo(self._fifo_in)
        except OSError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to create ExaBGP fifo file '{self._fifo_in}': {err}") from None

        try:
            os.mkfifo(self._fifo_out)
        except OSError as err:  # pragma: no cover
            raise NsNetSimError(f"Failed to create ExaBGP fifo file '{self._fifo_out}': {err}") from None

        # Run ExaBGP within the network namespace
        try:
            self.run_in_ns_check_call(args, env=environment)
        except subprocess.CalledProcessError as err:
            raise NsNetSimError(f"Failed to start ExaBGP with configuration file '{self._configfile}': {err.stdout}") from None

    def _remove(self):
        """Remove the router."""

        # Grab PID of the process...
        if os.path.exists(self._pidfile):
            try:
                with open(self._pidfile, "r") as pidfile_file:
                    pid = int(pidfile_file.read())
            except OSError as err:  # pragma: no cover
                raise NsNetSimError(f"Failed to open PID file '{self._pidfile}' for writing: {err}") from None
            # Terminate process
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:  # pragma: no cover
                self._log_warning(f"Failed to kill ExaBGP process PID {pid}")
            # Remove pid file
            try:
                os.remove(self._pidfile)
            except FileNotFoundError:  # pragma: no cover
                pass

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
