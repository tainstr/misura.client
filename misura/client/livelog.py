#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from datetime import datetime
import functools
import numpy as np

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
from misura.client import _
from live import registry

def color_level(level):
    if level>=40:
        return QtGui.QColor('red')
    elif level>=30:
        return QtGui.QColor('orange')
    elif level>=20:
        return QtGui.QColor('blue')
    return QtGui.QColor('black')   

def decorate(level, role):
    if role == Qt.FontRole:
        current_font = QtGui.QFont()
        current_font.setBold(level>=30)
        current_font.setItalic(level<10)
        return current_font
    
    if role == Qt.ForegroundRole:
        color = color_level(level)
        return QtGui.QBrush(color)

class AbstractLogModel(QtCore.QAbstractTableModel):
    level = 0
    actions = []
    
    def __init__(self, max_rows=1e4, parent=None):
        QtCore.QAbstractTableModel.__init__(self)
        #super(AbstractLogModel, self).__init__(self, parent=parent)
        self._header_data = ['Time', 'Message']
        self._data = []
        self.max_rows=1e4
        self.current_buf = []
        self._levels = []
        self._filtered = []
        
    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self._filtered)

    def columnCount(self, index=QtCore.QModelIndex()):
        if self.rowCount() == 0:
            return 0
        return len(self._header_data)
        
    def decode_row(self, row):
        return list(row)
        
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        data_idx = self._filtered[index.row()]
        row = self.decode_row(self._data[data_idx])
        level = row.pop(1)
        if role == QtCore.Qt.UserRole:
            return level
        if role in [Qt.ForegroundRole, Qt.FontRole]:
            return decorate(level, role)
        col = index.column()
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return
        return row[col]
    
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            return self._header_data[section] 
        
    def set_level(self, new_level=None):
        if new_level is None:
            update = False
            new_level = self.level
        else:
            update = True
            
        for j, a in enumerate(self.actions):
            nl = j*10
            if nl==new_level:
                # Was unchecked
                if update and not a.isChecked():
                    new_level += 10
            a.setChecked(new_level<=nl)
            
            if a.isChecked():
                px = QtGui.QPixmap(16,16)
                px.fill(color_level(nl))
                icon = QtGui.QIcon(px)
                a.setIcon(icon)
            else:
                a.setIcon(QtGui.QIcon())
                
        self.level = new_level
        self._filtered = list(np.where(np.array(self._levels)>self.level)[0])
        if update:
            self.modelReset.emit()
    
    def build_menu(self, menu):
        self.actions = []
        for i, name in enumerate((_('Debug'), _('Info'), _('Warning'), _('Error'), _('Critical'))):
            i *= 10
            act = menu.addAction(name, functools.partial(self.set_level, i))
            act.setCheckable(True)
            self.actions.append(act)
            act.setFont(decorate(i, role=QtCore.Qt.FontRole))
            
        self.set_level()
  

class LiveLogModel(AbstractLogModel):
    def __init__(self, max_rows=1e4, parent=None):
        AbstractLogModel.__init__(self, max_rows)
        
    def append(self, buf):
        if buf == self.current_buf:
            logging.debug('No new log')
            return
        app = 0
        
        for line in buf:
            if type(line) != type([]):
                continue
            if len(line) < 2:
                continue
            if line in self.current_buf:
                continue
            st = datetime.fromtimestamp(line[0]).strftime('%X')
            p = line[1]
            fmsg = line[3].strip('\n')
            self._data.append((st, p, fmsg))
            self._levels.append(p)
            if p>=self.level:
                self._filtered.append(len(self._levels))
            app+=1

        rm = len(self._data) - self.max_rows
        if rm>0:
            self._data = self._data[:-rm]
            self._levels = self._levels[:-rm]
            self._filtered = [f-1 for f in self._filtered[:-rm]]
                
         
        self.current_buf = buf[:]
        
        if app:
            QtCore.QAbstractTableModel.reset(self)


class LiveLog(QtGui.QTableView):
    iter = 0      
    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.log_model = LiveLogModel()
        self.setModel(self.log_model)
        self.label = _('Log')
        self.menu = QtGui.QMenu(self)
        self.menu.addAction(_('Update now'), self.slotUpdate)
        self.log_model.build_menu(self.menu)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setWordWrap(True)
        self.setTextElideMode(QtCore.Qt.ElideLeft)
        self.horizontalHeader().setStretchLastSection(True)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        if registry != None:
            self.connect(registry, QtCore.SIGNAL('log()'), 
                         self.slotUpdate, 
                         QtCore.Qt.QueuedConnection)
        self.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
        self.slotUpdate()
        
        
        
    def slotUpdate(self):
        if registry == None:
            logging.debug('No registry')
            return
        
        self.log_model.append(registry.log_buf)
        self.iter +=1
        if self.iter == 10:
            self.resizeRowsToContents()
            #self.resizeColumnsToContents()
 

    def update(self):
        registry.update_log()

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))
        
