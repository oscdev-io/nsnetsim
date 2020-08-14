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

"""Generic node support."""

from typing import Callable, Optional


class GenericNode:
    """GenericNode implements a generic topology node."""

    # Name of the node
    _name: str
    # Logger
    _logger: Optional[Callable[[str], None]]
    # Extra logging info
    _extra_log: str

    def __init__(self, name, logger, **kwargs):
        """Initialize the object."""

        # Set the node name
        self._name = name

        # Set the logger to use
        self._logger = logger

        # Extra logging info
        self._extra_log = ""

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

    @property
    def name(self):
        """Return the node name."""
        return self._name

    def _init(self, **kwargs):
        """Initialize this node, should be overridden in child classes."""
        return kwargs

    def _create(self):
        """Create this node, should be overridden in child classes."""
        raise NotImplementedError('The _create() method should be defined in the child class')

    def _remove(self):
        """Remove this node, should be overridden in child classes."""
        raise NotImplementedError('The _remove() method should be defined in the child class')

    def _log(self, msg: str):
        """Log a message either using the logger provided or just using print."""

        node_type = type(self).__name__
        newmsg = f'[{node_type}] {msg}'

        if self._logger:
            self._logger(newmsg)
        else:
            print(newmsg)
