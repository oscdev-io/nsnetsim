"""Namespace Network Simulator."""

import re
from setuptools import find_packages, setup

main_py = open('nsnetsim/__init__.py').read()
metadata = dict(re.findall("__([A-Z]+)__ = '([^']+)'", main_py))

NAME = 'nsnetsim'
VERSION = metadata['VERSION']

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

setup(
    name=NAME,
    version=VERSION,
    author="Nigel Kukard",
    author_email="nkukard@lbsd.net",
    description="Network namespace network simulator",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://gitlab.devlabs.linuxassist.net/allworldit/python/nsnetsim",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.6',
    install_requires =[
        'birdclient',
    ],

    packages=find_packages(),
)
