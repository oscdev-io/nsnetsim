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

"""Generic node support."""

import logging
import subprocess  # nosec


class GenericNode:
    """GenericNode implements a generic topology node."""

    # Name of the node
    _name: str
    # Extra logging info
    _extra_log: str
    # Debug mode
    _debug: bool

    def __init__(self, name: str, **kwargs):
        """Initialize the object."""

        # Set the node name
        self._name = name

        # Extra logging info
        self._extra_log = ""

        # Check if we have a debug flag
        self._debug = kwargs.get("debug", False)

        # Call the nodes initialization function
        self._init(name=name, **kwargs)

    def create(self):
        """Create the node."""

        self._log(f'Creating node "{self.name}"{self._extra_log}')
        self._create()

    def remove(self):
        """Remove the node."""

        self._log(f'Removing "{self.name}"{self._extra_log}')
        self._remove()

    def run_check_call(self, args, **kwargs) -> subprocess.CompletedProcess:
        """Run command inside the namespace similar to check_call."""
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, text=True, **kwargs)  # nosec

    def run_check_output(self, args, **kwargs) -> subprocess.CompletedProcess:
        """Run command inside the namespace similar to check_call."""
        return subprocess.run(args, capture_output=True, check=True, text=True, **kwargs)  # nosec

    @property
    def name(self):
        """Return the node name."""
        return self._name

    def _init(self, **kwargs):
        """Initialize this node, should be overridden in child classes."""
        raise NotImplementedError("The _init() method should be defined in the child class")

    def _create(self):
        """Create this node, should be overridden in child classes."""
        raise NotImplementedError("The _create() method should be defined in the child class")

    def _remove(self):
        """Remove this node, should be overridden in child classes."""
        raise NotImplementedError("The _remove() method should be defined in the child class")

    def _log(self, msg: str):
        """Log a message."""

        node_type = type(self).__name__

        logging.info("[%s] %s", node_type, msg)

    def _log_warning(self, msg: str):  # pragma: no cover
        """Log a message."""

        node_type = type(self).__name__

        logging.warning("[%s] %s", node_type, msg)
