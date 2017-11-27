#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

from .ipyslurm import IPySlurm


def load_ipython_extension(ipython):
    ipython.register_magics(IPySlurm)
