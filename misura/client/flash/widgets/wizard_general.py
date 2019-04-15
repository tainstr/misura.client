#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Wizard: general options page (1st)."""
from misura.client import _, iutils, widgets, conf
from collections import OrderedDict
from PyQt4 import QtGui, QtCore
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

def set_global_option(conf, key, old, val):
    from misura.client.live import registry
    kids = []
    for smp in conf.parent().samples:
        smp[key] = val
        kids.append(smp.getattr(key, 'kid'))
    registry.force_redraw(kids)
    return val

def get_global_option(conf, key, old, val):
    values = []
    options = []
    current = set()
    for smp in conf.parent().samples:
        current.add(smp[key])
        if smp.hasattr(key, 'values'):
            values += list(smp.getattr(key, 'values'))
        options += list(smp.getattr(key, 'options'))
        print(smp['devpath'], current, values, options)
    if len(current)==1:
        val = current.pop()
    else:
        val = 'None'
    conf.setattr(key, 'options', list(OrderedDict.fromkeys(options))+['Not uniform'])
    if values:
        conf.setattr(key, 'values', list(OrderedDict.fromkeys(values))+['None'])
    return val

def sample_title(smp):
    title = [smp['devpath'].capitalize(), smp['name']]
    title.append('L={:.4f}'.format(smp['thickness']))
    title.append('D={:.4f}'.format(smp['diameter']))
    return '; '.join(title)

class FlashWizardGeneral(QtGui.QScrollArea):
    def __init__(self, cfg, parent=None):
        """Test `cfg` proxy"""
        super(FlashWizardGeneral, self).__init__(parent=parent)
        self.setWindowTitle('Flash Wizard - General (1)')
        self.setMaximumWidth(600)
        self.setWidgetResizable(True)
        self.cfg = cfg
        self.base = QtGui.QWidget()
        self.base.setLayout(QtGui.QVBoxLayout())
        
        self.virtual = QtGui.QWidget(parent=self.base)
        self.lay = QtGui.QFormLayout()
        self.virtual.setLayout(self.lay)
        self.base.layout().addWidget(self.virtual)
        flash = cfg.flash
        
        # Global model
        fitopt = flash.measure.gete('fitting')
        fitting = widgets.build(cfg, flash.measure, fitopt, parent=self)
        #self.lay.addRow(fitting.label_widget, fitting)
        
        # Virtual global sample
        fakesmp = flash.sample1.copy(deep=True)
        fakesmp.callbacks_set = fakesmp.callbacks_set.copy()
        fakesmp.callbacks_set.add(set_global_option)
        fakesmp.callbacks_get = fakesmp.callbacks_get.copy()
        fakesmp.callbacks_get.add(get_global_option)
        
        # Global reference
        refopt = fakesmp.gete('diffusivityFile')
        refopt['callback_set'] = 'set_global_option'
        refopt['callback_get'] = 'get_global_option'
        fakesmp.sete('diffusivityFile', refopt)
        ref = widgets.build(fakesmp, fakesmp, refopt, parent=self)
        
        # Global laser geometry
        laser_opt = fakesmp.gete('laserGeometry')
        laser_opt['callback_set'] = 'set_global_option'
        laser_opt['callback_get'] = 'get_global_option'
        fakesmp.sete('laserGeometry', laser_opt)
        laser = widgets.build(fakesmp, fakesmp, laser_opt, parent=self)
        
        self.global_widgets = [fitting, ref, laser]
        
        for wg in self.global_widgets:
            self.lay.addRow(wg.label_widget, wg)
        
        secs = 0
        for smp in flash.samples:
            sec = self.add_sample(smp)
            if secs:
                sec.setChecked(False)
                sec.collapse()
            secs += 1
        self.base.layout().addStretch(10)
        self.setWidget(self.base)
        self.base.show()
        
    
    def add_sample(self, smp):
        prop_list = [smp.gete(key) for key in ('diffusivityFile', 'laserGeometry')]
        sec = conf.Section(smp, smp, prop_list, title=sample_title(smp), parent=self.base)
        #sec.setMinimumHeight(200)
        self.base.layout().addWidget(sec)
        return sec
        
          
        
        
        