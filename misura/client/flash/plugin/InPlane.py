#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run a model in a veusz plugin"""
import os
from pickle import loads

from veusz import plugins

from ..model import inplane

from AbstractModel import AbstractFlashModelPlugin

from misura.client.plugin.PlotPlugin import bounded_axes
bounded_axes['flash'].update(
    {'inplane': 'Diffusivity', 'theory': 'Signal'})


class InPlanePlugin(AbstractFlashModelPlugin):
    """Run In-Plane model fitting."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'In-Plane')
    # unique name for plugin
    name = 'In-Plane'
    # name to appear on status tool bar
    description_short = 'Run One Dimensional In-Plane model fitting'
    # text to appear in dialog box
    description_full = 'Run One Dimensional In-Plane model fitting'

    _params_class = inplane.InPlaneParams
    




# TODO: Separate system for auto-recursion of sub-ordered nodes?
plugins.toolspluginregistry.append(InPlanePlugin)
