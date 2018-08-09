#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon import reference
from PyQt4 import QtGui, QtCore

from misura.client import _
from misura.client.livelog import AbstractLogModel

class ReferenceLogModel(AbstractLogModel):
    def __init__(self, proxy, max_rows=1e4, parent=None):
        AbstractLogModel.__init__(self, max_rows)
        #super(ReferenceLogModel, self).__init__(max_rows, parent=None)
        self.proxy = proxy
        
    def get_log_paths(self):
        return self.proxy.header(['Log'])
    
    def set_log_path(self, path):
        self._data = reference.get_node_reference(self.proxy, path)
        self.modelReset.emit()
        
    def decode_row(self, row):
        return float(row[0]), int(row[1][0]), unicode(row[1][1])
        

    
class OfflineLog(QtGui.QTableView):
    iter = 0      
    def __init__(self, proxy, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.setModel(ReferenceLogModel(proxy))
        self.label = _('Log')
        self.menu = QtGui.QMenu(self)
        
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setWordWrap(True)
        self.setTextElideMode(QtCore.Qt.ElideLeft)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
        self.model().set_log_path('/log')
        

    def showMenu(self, pt):
        self.menu.clear()
        for p in self.model().get_log_paths():
            func = functools.partial(self.model().set_log_path, p)
            self.menu.addAction(p, func)
        self.menu.popup(self.mapToGlobal(pt))
        
