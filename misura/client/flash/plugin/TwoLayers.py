#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run a model in a veusz plugin"""
import os
from pickle import loads

from veusz import plugins
from misura.client import _
from misura.client.plugin.PlotPlugin import bounded_axes

from thegram.model import two_layers

from AbstractModel import AbstractFlashModelPlugin, fallback, confdb


bounded_axes['flash'].update(
    {'twolayers': 'Diffusivity', 'theory': 'Signal'})


class TwoLayersPlugin(AbstractFlashModelPlugin):
    """Run TwoLayers model fitting."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'Two Layers')
    # unique name for plugin
    name = 'Two Layers'
    # name to appear on status tool bar
    description_short = 'Run Two Layers model fitting'
    # text to appear in dialog box
    description_full = 'Run Two Layers model fitting'

    _params_class = two_layers.TwoLayersParams
    guess_diffusivity_suffix = '2'
   


# TODO: Separate system for auto-recursion of sub-ordered nodes?
plugins.toolspluginregistry.append(TwoLayersPlugin)
