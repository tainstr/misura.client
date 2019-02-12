#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
import os
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import functools
from .. import _
from .DatabaseModel import DatabaseModel
from .DatabaseHeader import DatabaseHeader



def iter_selected(table_view):
    """Iterate over selected rows returning their corresponding sql record"""
    column_count = table_view.model().columnCount()
    for row in table_view.selectionModel().selectedRows():
        r = []
        row = row.row()
        for i in range(column_count):
            idx = table_view.model().index(row, i)
            r.append(table_view.model().data(idx))
        yield r


def get_delete_selection(table_view):
    records = []
    for record in iter_selected(table_view):
        records.append(record)
    n = min(len(records), 10)
    N = len(records)
    msg = '\n'.join([r[3] for r in records[:n]])
    msg = _("You are going to delete {} files, including:").format(
        N) + '\n' + msg
    ok = QtGui.QMessageBox.question(table_view,
                                    _("Permanently delete test data?"), msg,
                                    QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                                    QtGui.QMessageBox.Cancel)
    if ok != QtGui.QMessageBox.Ok:
        logging.debug('Delete aborted')
        return []
    return records


class DatabaseTable(QtGui.QTableView):
    menu_add_to = False
    selected_tab_index = -1
    def __init__(self, remote=False, parent=None, browser=False):
        QtGui.QTableView.__init__(self, parent)
        self.remote = remote
        self.browser = browser
        self.curveModel = DatabaseModel(remote)
        self.setModel(self.curveModel)
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)
        
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtGui.QAbstractItemView.EditKeyPressed)
        self.connect(
            self, QtCore.SIGNAL('doubleClicked(QModelIndex)'), self.select)
        self.reset_header()
        
        self.setSortingEnabled(True)
        
        self.menu = QtGui.QMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        
        self.menu.addAction(
            _('Open selected tests'), lambda: self.select(None))
        
        if self.browser:
            self.menu_add_to = self.menu.addMenu(_('Add to...'))
        
        self.menu.addAction(_('Edit Name'), self.edit_name)
        self.menu.addAction(_('Edit Comment'), self.edit_comment)
            
        self.menu.addAction(_('View folder'), self.view_folder)
        self.menu.addAction(_('Delete'), self.delete)
        
    def reset_header(self):
        hh = DatabaseHeader(parent=self)
        self.setHorizontalHeader(hh)
        hh.show()
        return hh
        
    def ncol(self, name):
        return self.model().ncol(name)
        
    def edit_name(self):
        record = self.selectionModel().selectedIndexes()[0]
        record = record.sibling(record.row(), self.ncol('name'))
        self.scrollTo(record)
        self.edit(record)
    
    def edit_comment(self):
        record = self.selectionModel().selectedIndexes()[0]
        record = record.sibling(record.row(), self.ncol('comment'))
        self.scrollTo(record)
        self.edit(record)

    def showMenu(self, pt):
        if self.menu_add_to:
            self.menu_add_to.clear()
            for i,tab in enumerate(self.browser.list_tabs()[1:]):
                open_function = functools.partial(self.add_to_tab,i+1)
                self.menu_add_to.addAction(tab.title, open_function)
        self.menu.popup(self.mapToGlobal(pt))
        
        

    def select(self, idx=-1):
        self.selected_tab_index = -1
        self.emit(QtCore.SIGNAL('selected()'))
        
    def add_to_tab(self, tab_index):
        self.selected_tab_index = tab_index
        self.emit(QtCore.SIGNAL('selected()'))
        

    def getName(self):
        idx = self.currentIndex()
        model = self.model()
        if not idx.isValid() or not (0 <= idx.row() <= model.rowCount()):
            return False, False, False
        ncol = model.header.index('name')
        icol = model.header.index('file')
        fcol = model.header.index('id')
        fuid = model.header.index('uid')
        row = model.tests[idx.row()]
        # name,index,file
        return row[ncol], row[icol], row[fcol], row[fuid]

    def view_folder(self):
        record = iter_selected(self).next()
        url = 'file:///' + os.path.dirname(record[0])
        logging.debug('opening file folder at', url)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def delete(self):
        """Delete selected records from remote server"""
        for record in get_delete_selection(self):
            self.remote.remove_uid(record[2])
        self.model().select()
