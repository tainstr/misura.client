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


class DatabaseModel(QtCore.QAbstractTableModel):
    
    def __init__(self, remote=False, tests=[], header=[]):
        QtCore.QAbstractTableModel.__init__(self)
        self.remote = remote
        self.tests = tests
        self.header = header
        self.orderby = 4
        self.order = 'DESC'
        self.limit = 1000
        self.offset = 0
        self.table = False
        
    def ncol(self, name):
        if name not in self.header:
            return -1
        return self.header.index(name)
    
    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.tests)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.header)
    
    def get_len(self):
        return self.remote.get_len(self.table)
    
    def has_next(self):
        return self.offset+self.limit<self.get_len()
    
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
        N=self.get_len()/self.limit
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
        if role == QtCore.Qt.DecorationRole and col==self.ncol('instrument'):
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
        name_column = self.ncol('name')
        comment_column = self.ncol('comment')
        uid = self.tests[index.row()][self.ncol('uid')]
        name = self.tests[index.row()][name_column]
        file_name = self.tests[index.row()][self.ncol('file')]

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

        if self.table=='test' and (index.column() == self.ncol('name') or index.column() == self.ncol('comment')):
            flags = flags | QtCore.Qt.ItemIsEditable

        return QtCore.Qt.ItemFlags(flags)
    
    def sort(self, column, order):
        self.orderby = column
        self.order = ['DESC', 'ASC'][order]
        self.select()

    def select(self):
        self.up()
        
    def update_header(self):
        self.header = self.remote.header(self.table)
        return self.header

    def up(self, conditions={}, operator=1):
        """TODO: rename to select()"""
        if not self.remote:
            return
        if not self.table:
            return
        
        oby = self.orderby 
        if oby<0 or oby>=len(self.header):
            oby = self.ncol('zerotime')
        if oby>=0:
            oby = self.header[oby]
        else:
            oby = False
        
        self.beginResetModel()
        self.tests = self.remote.query(conditions, operator, oby, 
                        self.order, self.limit, self.offset, self.table)
        
        self.sheader = []
        for h in self.header:
            translation_key = 'dbcol:' + h
            translation = _(translation_key, context="Option")
            if translation == translation_key:
                translation = h.capitalize()

            self.sheader.append(translation)
        self.resetInternalData()
        self.endResetModel()
        
        