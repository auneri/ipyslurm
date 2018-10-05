#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

from .ipyslurm import IPySlurm

__version__ = '1.1.0'


def load_ipython_extension(ipython):
    ipython.register_magics(IPySlurm)
