#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
import os
from misura.canon.logger import Log as logging
import datetime
import functools
from misura.client import _
from misura.canon import csutil, indexer


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

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.tests)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.header)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        row = self.tests[index.row()]
        col = index.column()
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

    def select(self):
        self.up()

    def up(self, conditions={}, operator=1):
        """TODO: rename to select()"""
        if not self.remote:
            return
        self.tests = self.remote.query(conditions, operator)
        self.header = self.remote.header()
        self.sheader = []
        for h in self.header:
            translation_key = 'dbcol:' + h
            translation = _(translation_key, context="Option")
            if translation == translation_key:
                translation = h.capitalize()

            self.sheader.append(translation)

        QtCore.QAbstractTableModel.reset(self)


class DatabaseHeader(QtGui.QHeaderView):

    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None):
        QtGui.QHeaderView.__init__(self, orientation, parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.show_menu)
        self.menu = QtGui.QMenu(self)
        self.cols = {}

    def show_menu(self, pt):
        QtGui.qApp.processEvents()
        self.menu.clear()
        for i, h in enumerate(self.model().sheader):
            act = self.menu.addAction(h, functools.partial(self.switch, i))
            act.setCheckable(True)
            act.setChecked((not self.isSectionHidden(i)) * 2)
        self.menu.popup(self.mapToGlobal(pt))

    def switch(self, i):
        if self.isSectionHidden(i):
            self.showSection(i)
        else:
            self.hideSection(i)


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
        self.setHorizontalHeader(DatabaseHeader(parent=self))

        self.menu = QtGui.QMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)

        self.menu.addAction(
            _('Open selected tests'), lambda: self.select(None))
        
        if self.browser:
            self.menu_add_to = self.menu.addMenu(_('Add to...'))
            
        self.menu.addAction(_('View folder'), self.view_folder)
        self.menu.addAction(_('Delete'), self.delete)

    def showMenu(self, pt):
        if self.menu_add_to:
            self.menu_add_to.clear()
            for i,tab in enumerate(self.browser.list_tabs()[1:]):
                open_function = lambda: self.add_to_tab(i+1)
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
        # url = 'file://' +
        url = os.path.dirname(record[0])
        logging.debug('opening file folder at', url)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def delete(self):
        """Delete selected records from remote server"""
        for record in get_delete_selection(self):
            self.remote.remove_uid(record[2])
        self.model().select()


class DatabaseWidget(QtGui.QWidget):

    def __init__(self, remote=False, parent=None, browser=False):
        QtGui.QWidget.__init__(self, parent)
        self.remote = remote
        loc = remote.addr
        if loc == 'LOCAL':
            loc = remote.dbPath
        self.setWindowTitle(_('misura Database: ') + loc)
        self.label = _('misura Database')
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.menu = QtGui.QMenuBar(self)
        self.menu.setNativeMenuBar(False)
        self.lay.addWidget(self.menu)

        self.table = DatabaseTable(self.remote, self, browser=browser)
        self.lay.addWidget(self.table)
        self.connect(self.table, QtCore.SIGNAL('selected()'), self.do_selected)

        # Ricerca e controlli
        wg = QtGui.QWidget(self)
        lay = QtGui.QHBoxLayout()
        wg.setLayout(lay)
        self.lay.addWidget(wg)

        lay.addWidget(QtGui.QLabel(_('Query:')))
        self.qfilter = QtGui.QComboBox(self)
        lay.addWidget(self.qfilter)
        self.nameContains = QtGui.QLineEdit(self)
        lay.addWidget(self.nameContains)
        self.doQuery = QtGui.QPushButton(_('Apply'), parent=self)
        lay.addWidget(self.doQuery)

        self.connect(self.doQuery, QtCore.SIGNAL('clicked()'), self.query)
        self.connect(
            self.nameContains, QtCore.SIGNAL('returnPressed()'), self.query)

        self.menu.addAction(_('Refresh'), self.refresh)
        self.menu.addAction(_('Rebuild'), self.rebuild)
        self.bar = QtGui.QProgressBar(self)
        self.lay.addWidget(self.bar)
        self.bar.hide()

        self.resize(QtGui.QApplication.desktop().screen().rect().width(
        ) / 2, QtGui.QApplication.desktop().screen().rect().height() / 2)

    def rebuild(self):
        self.remote.rebuild()
        self.up()

    def refresh(self):
        self.remote.refresh()
        self.up()

    def up(self):
        logging.debug('%s', 'DATABASEWIDGET UP')
        self.table.model().up()
        header = self.table.model().header
        sh = self.table.model().sheader
        hh = self.table.horizontalHeader()
        self.qfilter.clear()
        self.qfilter.addItem(_('All'), '*')
        for i, h in enumerate(header):
            logging.debug('%s %s %s', 'qfilter', i, h)
            if hh.isSectionHidden(i):
                continue
            self.qfilter.addItem(_(sh[i]), h)

        self.table.horizontalHeader().moveSection(name_column, 0)
        self.table.horizontalHeader().moveSection(incremental_id_column, 1)
        self.table.horizontalHeader().moveSection(serial_column, 2)

        self.table.horizontalHeader().hideSection(id_column)
        self.table.horizontalHeader().hideSection(uid_column)
        self.table.horizontalHeader().hideSection(verify_column)
        self.table.horizontalHeader().hideSection(file_column)
        self.table.horizontalHeader().hideSection(flavour_column)

        self.table.resizeColumnToContents(name_column)
        # name_column =

    def query(self, *a):
        d = self.qfilter.itemData(self.qfilter.currentIndex())
        d = str(d)
        val = str(self.nameContains.text())
        if len(val)==0:
            return self.up()
        
        q={}
        if d=='*':
            operator = 0 #OR
            for col in ('file', 'serial', 'uid', 'id', 'instrument', 'flavour', 'name', 'comment'):
                q[col] = val
        else:
            operator = 1 # AND    
            q[d] = val
        self.table.model().up(q, operator)
        
    def emit_selected(self, filename):
        if self.table.selected_tab_index<0:
            self.emit(QtCore.SIGNAL('selectedFile(QString)'), filename)
        else:
            self.emit(QtCore.SIGNAL('selectedFile(QString, int)'), filename, self.table.selected_tab_index)

    def do_selected(self, tab_index=-1):
        filename_column_index = self.table.model().header.index('file')
        
        for row in iter_selected(self.table):
            filename = row[filename_column_index]
            self.emit_selected(filename)
        self.table.selected_tab_index = -1
        isGraphics = self.parent() is None
        if isGraphics:
            self.close()


class UploadThread(QtCore.QThread):

    def __init__(self, storage, filename, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.filename = filename
        self.storage = storage
        self.dia = QtGui.QProgressDialog(
            'Sending data to remote server', 'Cancel', 0, 100)
        self.connect(self.dia, QtCore.SIGNAL('canceled()'), self.terminate)
        self.connect(self, QtCore.SIGNAL('finished()'), self.dia.hide)
        self.connect(self, QtCore.SIGNAL('finished()'), self.dia.close)
        self.connect(self, QtCore.SIGNAL('value(int)'), self.dia.setValue)

    def show(self):
        self.dia.show()

    def sigfunc(self, i):
        self.emit(QtCore.SIGNAL('value(int)'), i)

    def run(self):
        csutil.chunked_upload(self.storage.upload, self.filename, self.sigfunc)
        self.emit(QtCore.SIGNAL('ok()'))


def getDatabaseWidget(path, new=False, browser=False):
    path = str(path)
    spy = indexer.Indexer(path, [os.path.dirname(path)])
    if new:
        spy.rebuild()
    idb = DatabaseWidget(spy, browser=browser)
    idb.up()
    return idb


def getRemoteDatabaseWidget(path):
    from .connection import addrConnection
    obj = addrConnection(path)
    if not obj:
        logging.debug('%s', 'Connection FAILED')
        return False
    idb = DatabaseWidget(obj.storage)
    idb.up()
