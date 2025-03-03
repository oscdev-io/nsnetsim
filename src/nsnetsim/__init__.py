#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2019-2025, AllWorldIT.
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

"""Namespace Network Simulator package."""

import birdclient
import packaging.version

from .exceptions import NsNetSimError
from .version import __version__

# Check we have a sufficiently new version of birdclient
if packaging.version.parse(birdclient.__version__) < packaging.version.parse("0.0.8"):
    raise NsNetSimError("nsnetsim requires birdclient version 0.0.8 or newer")

__all__ = ["__version__"]
