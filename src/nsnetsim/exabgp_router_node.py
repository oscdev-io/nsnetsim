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

"""ExaBGP router support."""

import getpass
import os
import signal
import subprocess
from typing import List

from .router_node import RouterNode

__version__ = "0.0.1"


class ExaBGPRouterNode(RouterNode):
    """ExaBGPRouterNode implements a network isolated ExaBGP router node."""

    # Configuration file
    _configfile: str
    # Control socket
    _namedpipe: str
    # PID file
    _pidfile: str

    def _init(self, **kwargs):
        """Initialize the object."""

        # Call parent create
        super()._init()

        # We should be getting a config file
        configfile = kwargs.get('configfile', None)
        # Check it exists
        if configfile and (not os.path.exists(configfile)):
            raise RuntimeError(f'ExaBGP config file "{configfile}" does not exist')
        # Set config file
        self._configfile = configfile

        # Set named pipe
        self._namedpipe = f'exabgp-{self._name}'
        self._pidfile = f'{self._rundir}/exabgp-{self._name}.pid'
        self._fifo_in = f'/run/{self._namedpipe}.in'
        self._fifo_out = f'/run/{self._namedpipe}.out'
        self._logfile = f'{self._namedpipe}.log'

        # We start out with no process
        self._exabgp_process = None

    def exabgpcli(self, args: List[str]) -> List[str]:
        """Send a query to ExaBGP."""

        cmdline = ['exabgpcli']
        cmdline.extend(args)

        # Now for the actual configuration, which is done using the environment
        environment = {}
        environment['exabgp.api.pipename'] = self._namedpipe

        res = self.run(cmdline, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return res.stdout.decode('utf-8').splitlines()

    def _create(self):
        """Create the router."""

        # Call parent create
        super()._create()

        # Work out the arguments we're going to pass
        args = ['ip', 'netns', 'exec', self.namespace,
                'exabgp']
        # If we were given a config file, add it
        if self._configfile:
            args.append(self._configfile)

        # Now for the actual configuration, which is done using the environment
        environment = {}
        environment['exabgp.api.pipename'] = self._namedpipe
        environment['exabgp.daemon.daemonize'] = 'true'
        environment['exabgp.daemon.pid'] = self._pidfile
        environment['exabgp.daemon.user'] = getpass.getuser()
        environment['exabgp.log.all'] = 'true'
        environment['exabgp.log.destination'] = self._logfile

        try:
            subprocess.check_output(['mkfifo', self._fifo_in, self._fifo_out])
        except subprocess.CalledProcessError as exception:
            output = exception.output.decode('utf-8').rstrip()
            self._log(f'ERROR: Failed to create ExaBGP fifo files: '
                      f'{output}')

        # Run ExaBGP within the network namespace
        try:
            subprocess.check_output(args, env=environment)
        except subprocess.CalledProcessError as exception:
            output = exception.output.decode('utf-8').rstrip()
            self._log(f'ERROR: Failed to start ExaBGP with configuration file "{self._configfile}": '
                      f'{output}')

    def _remove(self):
        """Remove the router."""

        # Grab PID of the process...
        if os.path.exists(self._pidfile):
            with open(self._pidfile, 'r') as pidfile_file:
                pid = int(pidfile_file.read())
            # Terminate process
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                self._log(f'WARNING: Failed to kill ExaBGP process {pid}')
            # Remove pid file
            try:
                os.remove(self._pidfile)
            except FileNotFoundError:
                pass

        # Remove fifo's
        if os.path.exists(self._fifo_in):
            os.remove(self._fifo_in)
        if os.path.exists(self._fifo_out):
            os.remove(self._fifo_out)

        # Call parent remove
        super()._remove()
