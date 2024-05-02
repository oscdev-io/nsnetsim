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

import contextlib
import datetime
import json
import os
import shutil
import signal
from typing import Any, Dict, List, Optional

from .exceptions import NsNetSimError
from .router_node import RouterNode

__all__ = ["StayRTRServerNode"]


class StayRTRServerNode(RouterNode):
    """StayRTRServerNode implements a network isolated StayRTR server node."""

    # Cache file
    _cache: str
    # SLURM file
    _slurmfile: Optional[str]
    # PID file
    _pidfile: str
    # Args
    _args: List[str]

    def _init(self, **kwargs: Any) -> None:
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
                "metadata": {"buildtime": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "vrps": 0},
                "roas": [],
            }
            with open(cache, "w", encoding="UTF-8") as cache_file:
                cache_file.write(json.dumps(cache_data))
        # Set cache to use
        self._cache = cache

        # We should be getting a config file
        self._slurmfile = kwargs.get("slurmfile")
        if self._slurmfile and not os.path.exists(self._slurmfile):  # pragma: no cover
            raise NsNetSimError(f'StayRTR config file "{self._slurmfile}" does not exist')

        self._pidfile = f"{self._rundir}/stayrtr.pid"

        self._args = kwargs.get("args", [])

    def _create(self) -> None:
        """Create the server."""

        # Call parent create
        super()._create()

        args = ["stayrtr", "-cache", self._cache]
        if self._slurmfile:
            args.extend(["-slurm", self._slurmfile])
        args.extend(self._args)

        environment: Dict[str, str] = {}

        # Fork StayRTR so we can save its PID
        pid = os.fork()
        if pid == 0:
            # Write out PID file
            with open(self._pidfile, "w", encoding="UTF-8") as pidfile_file:
                pidfile_file.write(str(os.getpid()))
            # Run StayRTR within the network namespace
            try:
                self.exec_in_ns(args, env=environment)
            except OSError as err:
                raise NsNetSimError(f"Failed to start StayRTR with SLURM file '{self._slurmfile}': {err}") from None
            # If we got here it's an error
            os._exit(1)
        elif pid < 0:
            raise NsNetSimError("Failed to fork StayRTR process")

    def _remove(self) -> None:
        """Remove the server."""

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
                self._log_warning(f"Failed to kill StayRTR process PID {pid}")
            # Remove pid file
            with contextlib.suppress(FileNotFoundError):
                os.remove(self._pidfile)

        # Call parent remove
        super()._remove()
