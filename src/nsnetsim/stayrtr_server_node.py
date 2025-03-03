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

"""StayRTR server support."""

import datetime
import json
import os
import pathlib
import shutil
import signal
import subprocess  # nosec: B404
from typing import Any

from .exceptions import NsNetSimError
from .router_node import RouterNode

__all__ = ["StayRTRServerNode"]


class StayRTRServerNode(RouterNode):  # pylint: disable=too-many-instance-attributes
    """StayRTRServerNode implements a network isolated StayRTR server node."""

    # Cache file
    _cache: str
    # SLURM file
    _slurmfile: str | None
    # PID file
    _pidfile: str
    # Log file
    _logfile: str | None
    # SSH key
    _ssh_key_file: str | None
    # SSH authorized keys
    _ssh_authorized_keys_file: str | None
    # Args
    _args: list[str]

    # Internal process
    _process: subprocess.Popen[str] | None

    def _init(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the object."""
        # Call parent create
        super()._init()

        # Make sure stayrtr path is returned by which
        if not shutil.which("stayrtr"):
            raise NsNetSimError("StayRTR binary not found in PATH")

        # Check if we were provided a cache
        cache = kwargs.get("cache")
        if not cache:
            cache = f"{self._rundir}/stayrtr.cache.json"
            # Grab UTC timestamp
            cache_data = {
                "metadata": {"buildtime": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "vrps": 0},
                "roas": [],
            }
            cache_file = pathlib.Path(cache)
            with cache_file.open("w", encoding="UTF-8") as f:
                f.write(json.dumps(cache_data))
        # Set cache to use
        self._cache = cache

        # We should be getting a config file
        self._slurmfile = kwargs.get("slurmfile")
        if self._slurmfile:
            slurmfile = pathlib.Path(self._slurmfile)
            if slurmfile.exists():  # pragma: no cover
                raise NsNetSimError(f'StayRTR config file "{self._slurmfile}" does not exist')

        self._pidfile = f"{self._rundir}/stayrtr.pid"
        self._logfile = kwargs.get("logfile")

        # Check if we have an SSH key and authorized keys file
        self._ssh_key_file = kwargs.get("ssh_key_file")
        self._ssh_authorized_keys_file = None
        if self._ssh_key_file:
            # Make sure the SSH key exists
            ssh_keyfile = pathlib.Path(self._ssh_key_file)
            if not ssh_keyfile.exists():  # pragma: no cover
                raise NsNetSimError(f'StayRTR SSH key file "{self._ssh_key_file}" does not exist')
            # Make sure we have an authorized keys file
            self._ssh_authorized_keys_file = kwargs.get("ssh_authorized_keys_file")
            if not self._ssh_authorized_keys_file:  # pragma: no cover
                raise NsNetSimError("SSH authorized keys 'ssh_authorized_keys' must be provided if SSH key 'ssh_key' is provided")
            ssh_authorized_keys_file = pathlib.Path(self._ssh_authorized_keys_file)
            if not ssh_authorized_keys_file.exists():
                raise NsNetSimError(f'StayRTR SSH authorized keys file "{self._ssh_authorized_keys_file}" does not exist')

        self._args = kwargs.get("args", [])

        self._process = None

    def _create(self) -> None:
        """Create the server."""

        # Call parent create
        super()._create()

        args = ["stayrtr", "-cache", self._cache]
        if self._slurmfile:
            args.extend(["-slurm", self._slurmfile])
        if self._ssh_key_file:
            args.extend(["-ssh.bind", ":22"])
            args.append("-ssh.method.key")
            args.extend(["-ssh.key", self._ssh_key_file])
        if self._ssh_authorized_keys_file:
            args.extend(["-ssh.auth.key.file", self._ssh_authorized_keys_file])
        args.extend(self._args)

        environment: dict[str, str] = {}

        logfile = self._logfile
        if not logfile:
            logfile = "/dev/null"

        # Start StayRTR process using subprocess.Popen
        logfile_f = open(logfile, "w", encoding="UTF-8")  # noqa: PTH123,SIM115
        self._process = self.run_in_ns_popen(args, env=environment, stdout=logfile_f, stderr=subprocess.STDOUT)

        # Write out PID file
        pidfile = pathlib.Path(self._pidfile)
        with pidfile.open("w", encoding="UTF-8") as f:
            f.write(str(self._process.pid))

    def _remove(self) -> None:
        """Remove the server."""

        # Kill process
        if self._process:
            # Try terminate
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            # If that doesn't work, force kill the entire group
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)

        # Call parent remove
        super()._remove()
