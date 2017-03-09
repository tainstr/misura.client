#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from time import strftime, time
from datetime import datetime

from PyQt4 import QtGui, QtCore

from misura.client import _
from live import registry


class LiveLogModel(QtCore.QAbstractTableModel):
    def __init__(self, max_rows=1e4):
        QtCore.QAbstractTableModel.__init__(self)
        self._header_data = ['Time', 'L', 'Message']
        self._data = []
        self.max_rows=1e4
        self.current_buf = []

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QtCore.QModelIndex()):
        if self.rowCount() == 0:
            return 0
        return len(self._data[0])

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        row = self._data[index.row()]
        col = index.column()
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return
        return row[col]

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            return self._header_data[section]
        
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
            app+=1


            if len(self._data) > self.max_rows:
                self._data.pop(0)
         
        self.current_buf = buf[:]
        
        if app:
            QtCore.QAbstractTableModel.reset(self)


    
class LiveLog(QtGui.QTableView):
    iter = 0      
    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.setModel(LiveLogModel())
        self.label = _('Log')
        self.menu = QtGui.QMenu(self)
        self.menu.addAction('Update now', self.slotUpdate)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setWordWrap(True)
        self.setTextElideMode(QtCore.Qt.ElideLeft)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        if registry != None:
            self.connect(registry, QtCore.SIGNAL('log()'), 
                         self.slotUpdate, 
                         QtCore.Qt.QueuedConnection)
        self.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
        self.slotUpdate()
        
        
        
    def slotUpdate(self):
        logging.debug('LiveLog.slotUpdate')
        if registry == None:
            logging.debug('No registry')
            return
        
        self.model().append(registry.log_buf)
        self.iter +=1
        if self.iter == 10:
            self.resizeRowsToContents()
            #self.resizeColumnsToContents()
 

    def update(self):
        logging.debug('LiveLog.update')
        registry.updateLog()

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))
        
