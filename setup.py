"""Namespace Network Simulator."""

from setuptools import find_packages, setup

NAME = 'nsnetsim'
VERSION = '0.0.1'

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

    packages=find_packages('src', exclude=['tests']),
    package_dir={'': 'src'},
)
