# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import datetime
from PyQt4 import QtCore, QtGui

from m3db import fields_PROVE

class TestListModel(QtCore.QAbstractTableModel):

    """Modello di dati per la tabella PROVE, contenente la lista di tutte le prove presenti nel database."""

    def __init__(self):
        QtCore.QAbstractTableModel.__init__(self)
        self.tests = []
        self.header = fields_PROVE

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.tests)

    def columnCount(self, index=QtCore.QModelIndex()):
        if not len(self.tests):
            return 0
        return len(self.tests[0])

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        if role == QtCore.Qt.DisplayRole:
            obj = self.tests[index.row()]
            if len(obj) <= index.column():
                return 0
            obj = obj[index.column()]
            # Converto in stringa se l'oggetto è datetime
            if type(obj) == type(datetime.datetime(1, 2, 3)):
                if obj.year > 1900:
                    obj = obj.strftime('%d %b %Y')
            return obj

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return None
        if role == QtCore.Qt.DisplayRole:
            return self.header[section]

    def setTests(self, tests):
        self.tests = tests
        QtCore.QAbstractTableModel.reset(self)


class TestsTable(QtGui.QTableView):

    """Visualizzazione tabellare delle prove contenute nel database."""

    def __init__(self, path='', parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.path = path
        self.curveModel = TestListModel()
        self.setModel(self.curveModel)
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSelectionModel(self.selection)
        self.setColumnWidth(0, 45)
        self.setColumnWidth(1, 50)
        self.setColumnWidth(2, 350)


