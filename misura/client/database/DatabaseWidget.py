#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from .. import _
from ..clientconf import confdb

from .DatabaseModel import *
from .DatabaseTable import DatabaseTable, iter_selected

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
        self.doQuery = QtGui.QPushButton(_('Search'), parent=self)
        lay.addWidget(self.doQuery)

        self.doClose = QtGui.QPushButton(_('Close'), parent=self)
        self.doClose.setCheckable(True)
        if not browser:
            self.doClose.setChecked(True)
            lay.addWidget(self.doClose)
        else:
            self.doClose.setChecked(False)
            self.doClose.hide()
            
        #######
        # PAGER
        self.doPrev = QtGui.QPushButton('<', parent=self)
        self.doPrev.setMaximumWidth(15)
        self.doPrev.clicked.connect(self.table.model().prev)
        lay.addWidget(self.doPrev)
        self.pager = QtGui.QSlider(QtCore.Qt.Horizontal, parent=self)
        self.pager.valueChanged.connect(self.table.model().set_page)
        lay.addWidget(self.pager)
        self.doNext = QtGui.QPushButton('>', parent=self)
        self.doNext.setMaximumWidth(15)
        self.doNext.clicked.connect(self.table.model().next)
        lay.addWidget(self.doNext)
                
        self.table.model().modelReset.connect(self.update_pages)

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

    def _rebuild(self):
        from .live import registry
        self.remote.tasks = registry.tasks
        self.remote.rebuild()
        self.up()
        
    def rebuild(self):
        from ..widgets import RunMethod
        r = RunMethod(self._rebuild)
        r.pid = 'Rebuilding database'
        r.abort = self.remote.abort
        QtCore.QThreadPool.globalInstance().start(r)        

    def _refresh(self):
        from ..live import registry
        self.remote.tasks = registry.tasks
        self.remote.refresh()
        self.up()
        
    def refresh(self):
        from ..widgets import RunMethod
        r = RunMethod(self._refresh)
        r.pid = 'Refreshing database'
        r.abort = self.remote.abort
        QtCore.QThreadPool.globalInstance().start(r)
        

    def up(self):
        logging.debug('DATABASEWIDGET UP')
        self.table.model().up()
        header = self.table.model().header
        sh = self.table.model().sheader
        hh = self.table.horizontalHeader()
        self.qfilter.clear()
        self.qfilter.addItem(_('All'), '*')
        for i, h in enumerate(header):
            logging.debug('qfilter', i, h)
            if hh.isSectionHidden(i):
                continue
            self.qfilter.addItem(_(sh[i]), h)
        
        hh = self.table.horizontalHeader()
        for logical, visual in ((name_column, 0),
                                (incremental_id_column, 1), 
                                (serial_column, 2)):
            vi = hh.visualIndex(logical)
            if 0<vi!=visual:
                hh.moveSection(vi, visual)

        hh.hideSection(id_column)
        hh.hideSection(uid_column)
        hh.hideSection(verify_column)
        hh.hideSection(file_column)
        hh.hideSection(flavour_column)

        self.table.resizeColumnToContents(name_column)
        self.update_pages()
        
    def update_pages(self):
        r=2
        if self.table.model().has_next():
            self.doNext.show()
            self.pager.show()
        else:
            self.doNext.hide()
            r-=1
        if self.table.model().has_prev():
            self.doPrev.show()
            self.pager.show()
        else:
            self.doPrev.hide()
            r-=1
        if r:
            current, pages = self.table.model().pages()
            self.pager.setMaximum(pages)
            self.pager.setValue(current)
        else:
            self.pager.hide()
        
        

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
        if self.doClose.isChecked():
            self.close()
            
def getDatabaseWidget(path, new=False, browser=False):
    if not os.path.exists(path):
        return False
    path = str(path)
    spy = indexer.Indexer(path, [os.path.dirname(path)], toi=confdb['toi'])
    if new:
        spy.rebuild()
    idb = DatabaseWidget(spy, browser=browser)
    idb.up()
    return idb


def getRemoteDatabaseWidget(path):
    from ..connection import addrConnection
    obj = addrConnection(path)
    if not obj:
        logging.debug('Connection FAILED')
        return False
    idb = DatabaseWidget(obj.storage)
    idb.up()
    
    
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



