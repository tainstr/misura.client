#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Programmatic interface construction utilities"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from time import time
import datetime
import functools
import os
import collections
from traceback import print_exc
import threading
from copy import deepcopy
from .. import _
from .. import widgets
from .. import iutils

from PyQt4 import QtGui, QtCore

COL_CHECK = 0
COL_LABEL = 1
COL_CURRENT = 2
COL_DEFAULT = 3
COL_BASE = 4

readonly_types = ['Float', 'Integer', 'String', 'TextArea']

def get_label(wg):
    if wg.type in readonly_types:
        return wg.readonly_label
    return wg

class ChronologyTable(QtGui.QTableWidget):
    def __init__(self, interface, parent=None):
        # Min 4 columns: check, label, current, default
        super(ChronologyTable, self).__init__(0, 4, parent=parent)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectColumns)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.virtual_widgets = {}
        self.interface = interface
        self.desc = deepcopy(self.interface.remObj.describe())
        self.setWindowTitle(_('Chronology for {}, {}').format(self.desc['name']['current'], 
                                                            self.desc['fullpath']['current']))
        self.header = ['?', _('Name'),_('Current'), _('Default')]
        
        self.widgets = {}
        self.default_widgets = {}
        self.virtual_widgets = collections.defaultdict(collections.defaultdict) # row: col: widget
        self.checks = {}
        self.chron = collections.defaultdict(collections.defaultdict) # time: row: widget
        # Create widgets and rows
        i = -1
        for key, opt in self.desc.copy().items():
            a = set(opt['attr'])
            ra = set(['Result', 'Status', 'ReadOnly'])
            if len(ra-a)<len(ra):
                self.desc.pop(key)
                continue
            if opt['type'] in ('ReadOnly','Hidden', 'Role','RoleIO', 'Meta'):
                self.desc.pop(key)
                continue
            chron = opt.get('chron', [[],[]])
            if opt['current']==opt['factory_default'] and not chron[0]:
                self.desc.pop(key)
                continue
            wg = widgets.build(self.remObj.root, self.remObj, opt)
            # Skip non-representable widgets
            if not wg:
                self.desc.pop(key)
                continue
            
            self.widgets[key] = wg
            self.checks[key] = QtGui.QCheckBox()
            
            # Shadow widget
            shadow = self.shadow(opt, opt['factory_default'])
            self.default_widgets[key] = shadow 
            
            i += 1
            
            # Generate chronology entries
            for j, t in enumerate(chron[0]):
                val = chron[1][j]
                cwg = self.shadow(opt, val)
                self.chron[t][i] = cwg
            
            
            self.insertRow(i)
            self.setCellWidget(i, COL_CHECK, self.checks[key])
            self.setCellWidget(i, COL_LABEL, wg.label_widget)
            self.setCellWidget(i, COL_CURRENT, get_label(wg))
            if opt['current']!=opt['factory_default']:
                self.setCellWidget(i, COL_DEFAULT, get_label(shadow))
                
        self.create_chron_columns()
        
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.selectionModel().currentColumnChanged.connect(self.select_column)
        
    def shadow(self, opt, val):
        #TODO: improve appearance of shadow widgets for table cells
        shadow_remObj = deepcopy(self.remObj)
        shadow_opt = deepcopy(opt)
        shadow_opt['current'] = val
        wg = widgets.build(shadow_remObj.root, shadow_remObj, shadow_opt)
        wg.get = lambda *a, **k: True
        wg.set = lambda *a, **k: True
        return wg
    
    def create_chron_columns(self):
        self.header = self.header[:COL_BASE]
        # Extract sorted time columns
        self.times = sorted(self.chron.keys(), reverse=True)
        t0 = time()

        # Expand column count
        self.setColumnCount(COL_BASE+len(self.times))
        for col, t in enumerate(self.times):
            t1 = datetime.timedelta(seconds=int(t0-t))
            self.header.append('-{}'.format(t1))
            for row, wg in self.chron[t].items():
                self.setCellWidget(row, COL_BASE+col, get_label(wg))
        
        self.setHorizontalHeaderLabels(self.header)
        
    def select_column(self, current, previous):
        col = current.column()
        if col<4:
            logging.debug('Clear selection')
            self.selectionModel().clearSelection()
        if col==0:
            return
        
        # Clean old virtuals
        for row, item in self.virtual_widgets.items():
            for col in item.keys():
                logging.debug('Removing', row, col)
                self.removeCellWidget(row, col)
        self.virtual_widgets = collections.defaultdict(collections.defaultdict) 
        
        
        if col<4:
            logging.debug('Null selection')
            return
        
        # List all times after selected t
        t = self.times[col-COL_BASE]
        
        for row in xrange(self.rowCount()):
            for col1, t1 in enumerate(self.times[:col-COL_BASE+1]):
                wg = self.chron[t1].get(row, False)
                if wg and col1!=col:
                    self.virtual_widgets[row][col] = wg
        
        # Set latest item on column
        for row, colwg in self.virtual_widgets.items():
            for col1, wg in colwg.items():
                wg = self.shadow(wg.prop, wg.current)
                self.setCellWidget(row, col, get_label(wg))
    
        
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        
    def apply_selection(self):
        pass     
        
        
    @property
    def remObj(self):
        return self.interface.remObj
        

#TODO: ChronologyWidget with apply/cancel button and options: un/select all + show default

