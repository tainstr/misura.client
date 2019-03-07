#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Programmatic interface construction utilities"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from time import time
import datetime
import functools
import collections
from copy import deepcopy
from .. import _
from .. import widgets


from PyQt4 import QtGui, QtCore

COL_CHECK = 0
COL_CURRENT = 1
COL_DEFAULT = 2
COL_BASE = 3

readonly_types = ['Float', 'Integer', 'String', 'TextArea']

def get_label(wg):
    if wg.type in readonly_types:
        return wg.readonly_label
    return wg

class ChronologyTable(QtGui.QTableWidget):
    sig_applied = QtCore.pyqtSignal()
    shadow_remObj = False
    
    def __init__(self, interface, parent=None):
        # Min 3 columns: check, current, default
        super(ChronologyTable, self).__init__(0, 3, parent=parent)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectColumns)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.virtual_widgets = {}
        self.interface = interface
        self.desc = deepcopy(self.interface.remObj.describe())
        self.setWindowTitle(_('Chronology for {}, {}').format(self.desc['name']['current'], 
                                                            self.desc['fullpath']['current']))
        self.header = ['?', _('Current'), _('Default')]
        
        self.widgets = {}
        self.default_widgets = {}
        self.virtual_widgets = collections.defaultdict(collections.defaultdict) # row: col: widget
        self.checks = {}
        self.keys = []
        self.vheader = []
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
            cur = opt['current']
            fd = opt['factory_default']
            if None in (cur, fd):
                continue
            if cur==fd and not chron[0]:
                self.desc.pop(key)
                continue
            wg = widgets.build(self.remObj.root, self.remObj, opt)
            # Skip non-representable widgets
            if not wg:
                self.desc.pop(key)
                continue
            
            i += 1
            self.insertRow(i)
            
            self.keys.append(key)
            self.widgets[key] = wg
            # Shadow widget
            shadow = self.shadow(opt, fd)
            self.default_widgets[key] = shadow
            
            # Checkbox widget
            c = QtGui.QCheckBox()
            f = functools.partial(self.toggled_check, i)
            c.toggled.connect(f)
            self.checks[key] = c 
            
            # Generate chronology entries
            for j, t in enumerate(chron[0]):
                val = chron[1][j]
                cwg = self.shadow(opt, val)
                self.chron[t][i] = cwg
            
            self.setCellWidget(i, COL_CHECK, self.checks[key])
            self.vheader.append(opt['name'])
            wg.label_widget.hide()
            self.setCellWidget(i, COL_CURRENT, get_label(wg))
            if cur!=fd:
                self.setCellWidget(i, COL_DEFAULT, get_label(shadow))
                
        self.create_chron_columns()
        self.setVerticalHeaderLabels(self.vheader)
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.selectionModel().currentColumnChanged.connect(self.select_column)
        
        # Check all rows:
        self.select_all()
        
    def toggled_check(self, row, status):
        logging.debug('toggled_check', row, status)
        item = self.verticalHeaderItem(row)
        f = item.font()
        f.setUnderline(status)
        item.setFont(f)
        
        
    def shadow(self, opt, val):
        #TODO: improve appearance of shadow widgets for table cells
        if not self.shadow_remObj:
            self.shadow_remObj = deepcopy(self.remObj)
            self.shadow_remObj.set = lambda *a, **k: None
        shadow_opt = deepcopy(opt)
        shadow_opt['current'] = val
        wg = widgets.build(self.shadow_remObj.root, self.shadow_remObj, shadow_opt)
        wg.label_widget.hide()
        wg.get = lambda *a, **k: True
        wg.set = lambda *a, **k: True
        return wg
    
    def create_chron_columns(self):
        # Extract sorted time columns
        self.times = sorted(self.chron.keys(), reverse=True)
        

        # Expand column count
        self.setColumnCount(COL_BASE+len(self.times))
        self.fill_chron_columns()
        
        
    def fill_chron_columns(self):
        t0 = time()
        self.header = self.header[:COL_BASE]
        for col, t in enumerate(self.times):
            t1 = datetime.timedelta(seconds=int(t0-t))
            self.header.append('-{}'.format(t1))
            for row, wg in self.chron[t].items():
                self.setCellWidget(row, COL_BASE+col, get_label(wg))
        
        self.setHorizontalHeaderLabels(self.header)
        
    def clean_virtuals(self):
        # Clean old virtuals
        for row, item in self.virtual_widgets.items():
            for col in item.keys():
                logging.debug('Removing', row, col)
                self.removeCellWidget(row, col)
        self.virtual_widgets = collections.defaultdict(collections.defaultdict) 
        
    def select_column(self, current, previous=None):
        col = current.column()
        if col==COL_CHECK:
            return
        
        self.clean_virtuals()
        
        if col<COL_BASE:
            logging.debug('Invalid selection')
            return
        Nt = len(self.times)
        # Check row by row (options)
        for row in xrange(self.rowCount()):
            # Skip if not checked
            if not self.is_row_checked(row):
                continue
            # Search nearest column in the past
            for j, t1 in enumerate(self.times[col-COL_BASE:]):
                wg = self.chron[t1].get(row, False)
                if j==0:
                    if wg:
                        break
                    continue
                
                col1 = j+col-COL_BASE
                # Nothing found: keep searching in the past
                if not wg:
                    continue
                # List only if different from current value
                if wg.current!=self.widgets[wg.handle].current:
                    self.virtual_widgets[row][col] = wg
                break
        
        # Set latest item on column
        for row, colwg in self.virtual_widgets.items():
            if not self.is_row_checked(row):
                continue
            for col1, wg0 in colwg.items():
                wg = self.shadow(wg0.prop, wg0.current)
                logging.debug('Setting virtual', row, col1, col, wg.handle, wg.current)
                lbl = get_label(wg)
                self.setCellWidget(row, col, lbl)
                lbl.show()
                
    
        
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        
    def is_row_checked(self, row):
        return self.checks[self.keys[row]].isChecked()
        
    def select_all(self):
        status = [self.checks[key].isChecked() for key in self.keys]
        # If all are checked, unselect all
        if sum(status)==len(status):
            st = False
        else:
            # Select all
            st = True
        logging.debug('select_all', st)
        map(lambda c: c.setChecked(st), self.checks.values())
        # Redraw virtual column
        if self.currentColumn()>=COL_BASE:
            self.select_column(self.currentIndex())
        
    def apply(self):
        col = self.currentColumn()
        if col<COL_DEFAULT:
            logging.debug('Cannot apply: invalid column')
            return False
        
        new_values = {}
        for row in xrange(self.rowCount()):
            key = self.keys[row]
            if not self.checks[key].isChecked():
                logging.debug('Skipping unchecked: ', key)
                continue
            if col==COL_DEFAULT:
                wg = self.default_widgets[key]
            elif self.virtual_widgets.get(row, {}).get(col, None):
                wg = self.virtual_widgets[row][col]
            else:
                logging.debug('Cannot find proper value for', key, row, col)
                continue
                
            new_values[key] = wg.current
            
        from misura.client.live import registry
        kids = []
        for key, value in new_values.items():
            self.remObj.set(key, value)
            kids.append(self.remObj.getattr(key, 'kid'))
        registry.force_redraw(kids)
        self.sig_applied.emit()
        
        
    @property
    def remObj(self):
        return self.interface.remObj
        

#TODO: ChronologyWidget with apply/cancel button and options: un/select all + show default

class ChronologyDialog(QtGui.QDialog):
    def __init__(self, interface, parent=None):
        super(ChronologyDialog, self).__init__(parent)
        lay = QtGui.QVBoxLayout()
        self.table = ChronologyTable(interface, parent=self)
        self.setWindowTitle(self.table.windowTitle())
        lay.addWidget(self.table)
        btn_select = QtGui.QPushButton(_('Un/select all'))
        btn_select.clicked.connect(self.table.select_all)
        lay.addWidget(btn_select)
        self.btn_apply = QtGui.QPushButton(_('Apply column values'))
        self.btn_apply.clicked.connect(self.table.apply)
        self.btn_apply.clicked.connect(self.accept)
        self.btn_apply.setEnabled(False)
        lay.addWidget(self.btn_apply)
        self.setLayout(lay)
        self.table.selectionModel().currentColumnChanged.connect(self.select_column)
        
    def select_column(self, current, previous):
        """Enabled/disable apply button"""
        en = current.column()>=COL_DEFAULT
        self.btn_apply.setEnabled(en)
        
        
    
    