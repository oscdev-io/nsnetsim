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

# Portions of this file have been derived from python-netns, Copyright (C) 2017-2019, Lars Kellogg-Stedman.

"""Network namespace support."""

import os


#
# Python doesn't expose the setns function, so we need to load it ourselves.
#
from ctypes import CDLL, get_errno

# Constants we need
CLONE_NEWNET = 0x40000000

def errcheck(ret, func, args): # noqa
    """Raise an OS error if something goes wrong."""
    if ret == -1:
        error = get_errno()
        raise OSError(error, os.strerror(error))

libc = CDLL('libc.so.6', use_errno=True) # noqa
libc.setns.errcheck = errcheck # noqa

#
# End of importing of setns
#


def setns(filefd, nstype):
    """Change the network namespace of the calling thread.

    Given a file descriptor referring to a namespace, reassociate the
    calling thread with that namespace.  The fd argument may be either a
    numeric file  descriptor or a Python object with a fileno() method.
    """

    if hasattr(filefd, "fileno"):
        filefd = filefd.fileno()

    return libc.setns(filefd, nstype)


def get_ns_path(nspath: str = None, nsname: str = None, nspid: int = None):
    """Generate a filesystem path from a namespace name or pid.

    Generate a filesystem path from a namespace name or pid, and return
    a filesystem path to the appropriate file.  Returns the nspath argument
    if both nsname and nspid are None.
    """

    if nsname:
        nspath = "/var/run/netns/%s" % nsname
    elif nspid:
        nspath = "/proc/%d/ns/net" % nspid

    if (not nspath) or (not os.path.exists(nspath)):
        raise ValueError("namespace path %s does not exist" % nspath)

    return nspath


class NetNS:
    """A context manager for running code inside a network namespace.

    This is a context manager that on enter assigns the current process
    to an alternate network namespace (specified by name, filesystem path,
    or pid) and then re-assigns the process to its original network
    namespace on exit.
    """

    # Our namespace handle
    _myns: str

    def __init__(self, nsname: str = None, nspath: str = "", nspid: int = None):
        """Initialize object."""

        # Grab paths
        self.mypath = get_ns_path(nspid=os.getpid())
        self.targetpath = get_ns_path(nspath=nspath, nsname=nsname, nspid=nspid)

        if not self.targetpath:
            raise ValueError("Invalid namespace")

    def __enter__(self):
        """Enter the namespace using with NetNS(...)."""
        # Save our current namespace, so we can jump back during __exit__
        self._myns = open(self.mypath)
        with open(self.targetpath) as filefd:
            setns(filefd, CLONE_NEWNET)

    def __exit__(self, *args):
        """Exit the namespace."""
        setns(self._myns, CLONE_NEWNET)
        self._myns.close()
