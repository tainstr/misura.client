#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
import os
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import datetime

from misura.client import parameters
from misura.canon import indexer
from .. import _


file_column = 0
serial_column = 1
uid_column = 2
id_column = 3
zero_time_column = 4
instrument_column = 5
flavour_column = 6
name_column = 7
elapsed_column = 8
number_of_samples_column = 9
comment_column = 10
verify_column = 11
incremental_id_column = 12

class DatabaseModel(QtCore.QAbstractTableModel):

    def __init__(self, remote=False, tests=[], header=[]):
        QtCore.QAbstractTableModel.__init__(self)
        self.remote = remote
        self.tests = tests
        self.header = header
        self.orderby = 'zerotime'
        self.order = 'DESC'
        self.limit = 1000
        self.offset = 0

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.tests)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.header)
    
    def has_next(self):
        return self.offset+self.limit<self.remote.get_len()
    
    def has_prev(self):
        return self.offset>0

    def next(self):
        self.offset+=self.limit
        self.select()
        
    def prev(self):
        self.offset -= self.limit
        if self.offset<5:
            self.offset = 0
        self.select()
        
    def pages(self):
        N=self.remote.get_len()/self.limit
        current = self.offset/self.limit
        return current, N
    
    def set_page(self, N):
        self.offset = N*self.limit
        self.select()
        

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        row = self.tests[index.row()]
        col = index.column()
        if role == QtCore.Qt.DecorationRole and col==instrument_column:
            instrument = row[col]
            icon = QtGui.QIcon(os.path.join(parameters.pathArt, 'small_' + instrument + '.svg'))
            return icon
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return
        val = row[col]
        if self.header[col] == 'elapsed':
            dt = datetime.timedelta(seconds=val)
            val = str(dt).split('.')[0]
        return val

    def setData(self, index, value, role):
        uid = self.tests[index.row()][uid_column]
        name = self.tests[index.row()][name_column]
        file_name = self.tests[index.row()][file_column]

        update_functions = {
            name_column: self.remote.change_name,
            comment_column: self.remote.change_comment
        }

        changed_lines = update_functions[index.column()](value, uid, file_name)

        self.up()
        return changed_lines

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            return self.sheader[section]

    def flags(self, index):
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

        if index.column() == name_column or index.column() == comment_column:
            flags = flags | QtCore.Qt.ItemIsEditable

        return QtCore.Qt.ItemFlags(flags)
    
    def sort(self, column, order):
        self.orderby=indexer.indexer.testColumnDefault[column]
        self.order = ['DESC', 'ASC'][order]
        self.select()

    def select(self):
        self.up()

    def up(self, conditions={}, operator=1):
        """TODO: rename to select()"""
        if not self.remote:
            return
        self.tests = self.remote.query(conditions, operator, self.orderby, 
                                       self.order, self.limit, self.offset)
        self.header = self.remote.header()
        self.sheader = []
        for h in self.header:
            translation_key = 'dbcol:' + h
            translation = _(translation_key, context="Option")
            if translation == translation_key:
                translation = h.capitalize()

            self.sheader.append(translation)

        QtCore.QAbstractTableModel.reset(self)