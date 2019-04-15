#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Wizard: shot selection page (2nd)."""
import tables
import numpy as np
from misura.client import _, iutils, widgets

from PyQt4 import QtGui, QtCore
from misura.canon.logger import get_module_logging
from misura.client.iutils import theme_icon
logging = get_module_logging(__name__)

from .wizard_general import sample_title

empty_legend = _('Please select target sample.')
sample_legend = _('Please select target temperature segment')
segment_legend = _('Please select target shot')
shot_legend = _('Review the shot and proceed to model prototyping.')
legends = [empty_legend, sample_legend, segment_legend, shot_legend]

SEL_EMPTY = 0
SEL_SAMPLE = 1
SEL_SEGMENT = 2
SEL_SHOT = 3


def select_item(list_wg, idx):
    for i in xrange(list_wg.count()):
        item = list_wg.item(i)
        f = item.font()
        f.setBold(i==idx)
        item.setFont(f)
        
        

class SelectShotTables(QtGui.QWidget):
    selected_shot = QtCore.pyqtSignal(str)
    current = ''
    
    def __init__(self, preselect, parent=None):
        """`preselect` proxy of test, sample, segment, or shot"""
        super(SelectShotTables, self).__init__(parent=parent)
        self.cfg = preselect.root
        self.lay = QtGui.QHBoxLayout()
        self.setLayout(self.lay)
        
        self.samples = QtGui.QListWidget(self)
        self.segments = QtGui.QListWidget(self)
        self.segments.setMaximumWidth(120)
        self.shots = QtGui.QListWidget(self)
        self.shots.setMaximumWidth(80)
        self.legend = QtGui.QLabel(empty_legend, parent=self)
        self.legend.setWordWrap(True)
        self.legend.setIndent(40)
        self.legend.setMinimumWidth(300)
        self.legend.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
        self.pix0 = theme_icon('go-next').pixmap(32,32)
        self.pix1 = theme_icon('go-next').pixmap(50,50)
        self.ico_sample = QtGui.QLabel()
        self.ico_sample.setPixmap(self.pix1)
        self.lay.addWidget(self.ico_sample)
        self.lay.addWidget(self.samples)
        
        self.ico_segment = QtGui.QLabel()
        self.ico_segment.setPixmap(self.pix0)
        self.lay.addWidget(self.ico_segment)
        self.lay.addWidget(self.segments)
        
        self.ico_shot = QtGui.QLabel()
        self.ico_shot.setPixmap(self.pix0)
        self.lay.addWidget(self.ico_shot)
        self.lay.addWidget(self.shots)
        self.lay.addWidget(self.legend)
        self.lay.insertStretch(100)
        for smp in self.cfg.flash.samples:
            self.samples.addItem(sample_title(smp))
            
        self.samples.currentRowChanged.connect(self.select_sample)
        
        self.icons = [self.ico_sample, self.ico_segment, self.ico_shot]
        self.legends = [empty_legend, sample_legend, segment_legend, shot_legend]
        
        if preselect!=self.cfg:
            self.select_path(preselect['fullpath'])
            
    def activate_selector(self, idx=SEL_EMPTY):
        self.legend.setText(legends[idx])
        for i, ico in enumerate(self.icons):
            pix = self.pix0
            if i==idx:
                pix = self.pix1
            ico.setPixmap(pix)

    def select_path(self, path):
        self.activate_selector(SEL_EMPTY)
        path = path.strip('/').split('/')
        if path.pop(0)!='flash':
            return False
        if not len(path):
            return False
        if not path[0].startswith('sample'):
            return False
        
        def find(obj_path, target):
            ret = False
            for i,obj in enumerate(target):
                if obj['devpath'] == obj_path:
                    ret = obj
                    break
            return i, ret
        
        i, smp = find(path.pop(0), self.cfg.flash.samples)
        if not smp:
            return False
        
        self.samples.setCurrentRow(i)
        self.activate_selector(SEL_SAMPLE)
        
        if not len(path):    
            return True
        
        i, sg = find(path.pop(0), smp.devices)
        if not sg:
            return False
        
        self.segments.setCurrentRow(i)
        self.activate_selector(SEL_SEGMENT)
        
        if not len(path):
            return True
        
        i, sh = find(path.pop(0), sg.devices)
        if not sh:
            return False
        
        self.shots.setCurrentRow(i)
        self.activate_selector(SEL_SHOT)
        return True
        
        
    def sorted_segments(self, smp):
        sorted_segments = smp.devices[:]
        sorted_segments.sort(key=lambda sg: sg['temperature'])
        return sorted_segments
        
    def select_sample(self, idx):
        select_item(self.samples, idx)
        smp = self.cfg.flash.samples[idx]
        self.segments.clear()
        self.shots.clear()
        for sg in self.sorted_segments(smp):
            self.segments.addItem(u'{:.1f}°C'.format(sg['temperature']))
            
        self.segments.currentRowChanged.connect(self.select_segment)
        self.current = ''
        self.selected_shot.emit(self.current)
        self.activate_selector(SEL_SAMPLE)


    def select_segment(self, idx):
        select_item(self.segments, idx)
        smp = self.cfg.flash.samples[self.samples.currentRow()]
        sg = self.sorted_segments(smp)[idx]
        self.shots.clear()
        for sh in sg.devices:
            self.shots.addItem(sh['devpath'])
        
        self.shots.currentRowChanged.connect(self.select_shot)
        self.current = ''
        self.selected_shot.emit(self.current)
        self.activate_selector(SEL_SEGMENT)
        
    def select_shot(self, idx):
        select_item(self.shots, idx)
        smp = self.cfg.flash.samples[self.samples.currentRow()]
        sg = self.sorted_segments(smp)[self.segments.currentRow()]
        sh = sg.devices[idx]
        self.current = sh['fullpath']
        self.selected_shot.emit(self.current)
        self.activate_selector(SEL_SHOT)
        
        
        
class FlashWizardSelectShot(QtGui.QWidget):
    def __init__(self, preselect, filename=False, parent=None):
        """`preselect` proxy of test, sample, segment, or shot
        `filename` from which to load the shot preview"""
        super(FlashWizardSelectShot, self).__init__(parent=parent)
        self.setWindowTitle('Flash Wizard - Shot selection (2)')
        self.cfg = preselect.root
        self.filename = filename
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        
        self.selector = SelectShotTables(preselect, parent=self)
        self.lay.addWidget(self.selector)
        
        self.preview = widgets.Profile(self)
        self.preview.setMinimumSize(500,200)
        self.lay.addWidget(self.preview)
        self.selector.selected_shot.connect(self.slot_selected_shot)
        if self.selector.current:
            self.slot_selected_shot(self.selector.current)
        
    def slot_selected_shot(self, shot_path):
        if len(shot_path)<3:
            self.preview.clear()
            return False
        f = tables.open_file(self.filename, mode='r')
        n = f.get_node(shot_path[:-1], 'raw')
        deplete = max(1, len(n) // 1000)
        y = np.array(n[::deplete]).astype(np.float32)
        y = max(y)-y
        x = n.attrs.t0+np.arange(len(n))*n.attrs.dt
        self.preview.update(x[::deplete],y)
        f.close()
        return True
        