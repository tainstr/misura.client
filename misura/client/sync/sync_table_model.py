#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore

class SyncTableModel(QtCore.QAbstractTableModel):
    def __init__(self, database, table_name):
        QtCore.QAbstractTableModel.__init__(self)
        self.database = database
        self.table_name = table_name
        self._header_data = []
        self._data = []
        self.where = False
        self.select()

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

    def setFilter(self,where=False):
        self.where = where

    def select(self):
        cmd = "SELECT * from {}".format(self.table_name)
        if self.where:
            cmd += ' WHERE {}'.format(self.where)
            self._data = self.database.execute_fetchall("SELECT * from {}".format(self.table_name))
            self._header_data = map(lambda row: row[1], self.database.execute_fetchall("pragma table_info({})".format(self.table_name)))
            QtCore.QAbstractTableModel.reset(self)
