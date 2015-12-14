#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
import os
from misura.canon.logger import Log as logging
import datetime
import functools
from misura.client import _
from misura.canon import csutil, indexer
from misura.client.clientconf import settings
from misura.client.connection import addrConnection


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
        if role != QtCore.Qt.DisplayRole:
            return
        val = row[col]
        if self.header[col] == 'elapsed':
            dt = datetime.timedelta(seconds=val)
            val = str(dt).split('.')[0]
        return val

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            return self.sheader[section]

    def up(self, conditions={}):
        if not self.remote:
            return
        self.tests = self.remote.query(conditions)
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


class DatabaseTable(QtGui.QTableView):

    def __init__(self, remote=False, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.remote = remote
        self.curveModel = DatabaseModel(remote)
        self.setModel(self.curveModel)
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.connect(
            self, QtCore.SIGNAL('doubleClicked(QModelIndex)'), self.select)
        self.setHorizontalHeader(DatabaseHeader(parent=self))
        # self.horizontalHeader().setMovable(True);

    def select(self, idx):
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


class DatabaseWidget(QtGui.QWidget):

    def __init__(self, remote=False, parent=None):
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

        self.table = DatabaseTable(self.remote, self)
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

        self.menu.addAction(_('Remove'), self.remove)
        self.menu.addAction(_('Refresh'), self.up)
        self.menu.addAction(_('Rebuild'), self.rebuild)
        self.bar = QtGui.QProgressBar(self)
        self.lay.addWidget(self.bar)
        self.bar.hide()

        self.resize(QtGui.QApplication.desktop().screen().rect().width() / 2, QtGui.QApplication.desktop().screen().rect().height() / 2)

    def rebuild(self):
        self.remote.rebuild()
        self.up()

    def up(self):
        logging.debug('%s', 'DATABASEWIDGET UP')
        self.table.model().up()
        header = self.table.model().header
        sh = self.table.model().sheader
        hh = self.table.horizontalHeader()
        self.qfilter.clear()
        self.qfilter.addItem(_('None'), '')
        for i, h in enumerate(header):
            logging.debug('%s %s %s', 'qfilter', i, h)
            if hh.isSectionHidden(i):
                continue
            self.qfilter.addItem(_(sh[i]), h)

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
        comment_cilumn = 10
        verify_column = 11
        incremental_id_column = 12

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


    def query(self):
        d = self.qfilter.itemData(self.qfilter.currentIndex())
        d = str(d)
        val = str(self.nameContains.text())
        if '' in [val, d]:
            return self.up()
        self.table.model().up({d: val})

    def do_selected(self):
        fname, filename, file, uid = self.table.getName()
        self.emit(QtCore.SIGNAL('selectedUid(QString)'), uid)
        self.emit(QtCore.SIGNAL('selectedFile(QString)'), filename)
        if self.remote.addr != 'LOCAL':
            self.emit(
                QtCore.SIGNAL('selectedRemoteUid(QString,QString)'), self.remote.addr, uid)


        isGraphics = self.parent() is None
        if isGraphics:
            self.close()




    def remove(self):
        fname, instr, file, uid = self.table.getName()
        self.remote.remove(uid)
        self.up()


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


def getDatabaseWidget(path, new=False):
    path = str(path)
    spy = indexer.Indexer(path, [os.path.dirname(path)])
    if new:
        spy.rebuild()
    idb = DatabaseWidget(spy)
    idb.up()
    return idb


def getRemoteDatabaseWidget(path):
    obj = addrConnection(path)
    if not obj:
        logging.debug('%s', 'Connection FAILED')
        return False
    idb = DatabaseWidget(obj.storage)
    idb.up()
