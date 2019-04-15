#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run a model in a veusz plugin"""
import os
from pickle import loads

from veusz import plugins

from thegram.model import gembarovic

from AbstractModel import AbstractFlashModelPlugin

from misura.client.plugin.PlotPlugin import bounded_axes
bounded_axes['flash'].update(
    {'gembarovic': 'Diffusivity', 'theory': 'Signal'})


class Gembarovic2DPlugin(AbstractFlashModelPlugin):
    """Run Gembarovic 2D model fitting."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'Gembarovic 2D')
    # unique name for plugin
    name = 'Gembarovic 2D'
    # name to appear on status tool bar
    description_short = 'Run Two Dimensional Gembarovic model fitting'
    # text to appear in dialog box
    description_full = 'Run Two Dimensional Gembarovic model fitting'

    _params_class = gembarovic.GembarovicParams


# TODO: Separate system for auto-recursion of sub-ordered nodes?
plugins.toolspluginregistry.append(Gembarovic2DPlugin)
