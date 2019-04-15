#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run a model in a veusz plugin"""
import os
from pickle import loads

from veusz import plugins

from misura.client import _
from misura.client.plugin.PlotPlugin import bounded_axes

from thegram.model import three_layers

from AbstractModel import AbstractFlashModelPlugin, fallback, confdb

bounded_axes['flash'].update(
    {'twolayers': 'Diffusivity', 'theory': 'Signal'})


class ThreeLayersPlugin(AbstractFlashModelPlugin):
    """Run ThreeLayers model fitting."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'Two Layers')
    # unique name for plugin
    name = 'Three Layers'
    # name to appear on status tool bar
    description_short = 'Run Three Layers model fitting'
    # text to appear in dialog box
    description_full = 'Run Three Layers model fitting'

    _params_class = three_layers.ThreeLayersParams
    guess_diffusivity_suffix = '2'

# TODO: Separate system for auto-recursion of sub-ordered nodes?
plugins.toolspluginregistry.append(ThreeLayersPlugin)
