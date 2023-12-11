[![pipeline status](https://gitlab.oscdev.io/software/nsnetsim/badges/master/pipeline.svg)](https://gitlab.oscdev.io/software/nsnetsim/commits/master)
[![coverage report](https://gitlab.oscdev.io/software/nsnetsim/badges/master/coverage.svg)](https://gitlab.oscdev.io/software/nsnetsim/commits/master)

# Namespace network simulator

The `nsnetsim` Python package provides the ability to simulate a network using network namespaces. This is extremely efficient
in terms of memory and disk resources. There is no 3rd-party software required.

Currently the nodes supported include `BirdRouterNode`, `ExaBGPRouterNode`, `RouterNode` and `SwitchNode`.

The `SwitchNode` is special as it accepts a list of interfaces created on any `RouterNode` to add to a virtual switch.

This software was written to simulate a core network of a international network carrier using BIRD and ExaBGP routers in order to
test the deployment of configuration on hundreds of devices and provide the ability to inspect each devices routing tables.

