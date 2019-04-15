#!/usr/bin/python
# -*- coding: utf-8 -*-
"""This entire module should be moved to misura.client after release. It would greatly improve the design!"""

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from misura.client.plugin.PlotPlugin import bounded_axes
if not bounded_axes.has_key('flash'):
    bounded_axes['flash'] = {}
      
bounded_axes['flash'].update({name: 'Diffusivity' for name in ('halftimes', 'parkers', 'koskis',
                                                          'heckmans', 'clarkTaylors', 'degiovannis', 
                                                          'clarkTaylor1s', 'references',
                                                          )})
bounded_axes['flash'].update({name: 'Signal' for name in ('raw', 'corrected')})  
bounded_axes['flash'].update({name: 'Pulse' for name in ('laser', 'laserFit')})  

import Baseline
import AbstractModel
import Gembarovic2D
import ModelPlotPlugin
import SummaryPlotPlugin
import ShotPlotPlugin
import InPlane
import TwoLayers
import ThreeLayers
import FlashShotImportPlugin

model_plugins = [Gembarovic2D.Gembarovic2DPlugin,
                 InPlane.InPlanePlugin,
                 TwoLayers.TwoLayersPlugin,
                 ThreeLayers.ThreeLayersPlugin
                 ]

models = {p._params_class.section_name: p for p in model_plugins}


def check_complete_shot(cfg, model_name):
    if not cfg:
        return False
    for model in cfg.devices:
        if 'model' in model and model['model']==model_name:
            return True
    return False

def check_complete_segment(cfg, model_name):
    if not cfg:
        return False
    if not 'shots' in cfg:
        # not a segment, disregard
        return True
    N = cfg['shots']
    for i in xrange(1, N+1):
        shot = cfg.child('N{}'.format(i))
        if not check_complete_shot(shot, model_name):
            logging.debug('Segment incomplete', model_name, cfg['fullpath'])
            return False
    return True

def check_complete_sample(cfg, model_name):
    if not cfg:
        return False
    for seg in cfg.devices:
        if not check_complete_segment(seg, model_name):
            logging.debug('Sample incomplete', model_name, cfg['fullpath'])
            return False
    return True

def check_complete_test(cfg, model_name):
    for smp in cfg.samples:
        if not check_complete_sample(smp, model_name):
            logging.debug('Test incomplete', model_name)
            return False
    return True