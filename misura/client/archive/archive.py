#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore
from .. import _
from .. import confwidget
from .. import filedata
from .. import misura3
from ..clientconf import confdb
from misura.client.database import getDatabaseWidget, getRemoteDatabaseWidget
import menubar
import testwindow


class MainWindow(QtGui.QMainWindow):

    """Open single files, local databases, remote databases."""

    def __init__(self, parent=None):
        super(QtGui.QMainWindow, self).__init__(parent)
        self.tab = QtGui.QTabWidget()
        self.area = QtGui.QMdiArea()
        self.tab.addTab(self.area, _('Databases'))
#       self.overview=QtGui.QWidget()
#       self.tab.addTab(self.overview,_('Overview'))
        self.tab.setTabsClosable(True)
        self.tab.setDocumentMode(True)
        self.setCentralWidget(self.tab)
        self.setMinimumSize(800, 600)
        self.setWindowTitle(_('Misura Browser'))
        self.myMenuBar = menubar.ArchiveMenuBar(parent=self)
        self.setMenuWidget(self.myMenuBar)

        self.connect(
            self.tab, QtCore.SIGNAL('tabCloseRequested(int)'), self.close_tab)

        self.connect(self.myMenuBar.recentFile, QtCore.SIGNAL(
            'select(QString)'), self.open_file)

        self.connect(self.myMenuBar.recentDatabase, QtCore.SIGNAL(
            'select(QString)'), self.open_database)
        self.connect(self.myMenuBar, QtCore.SIGNAL(
            'new_database(QString)'), self.new_database)

        self.connect(self.myMenuBar.recentM3db, QtCore.SIGNAL(
            'select(QString)'), self.open_m3db)

        # Recent objects greeter window:
        greeter = confwidget.Greeter(parent=self)
        self.connect(greeter.file, greeter.file.sig_select, self.open_file)
        self.connect(
            greeter.database, greeter.database.sig_select, self.open_database)
        win = self.area.addSubWindow(greeter)
        win.show()

    def close(self):
        # TODO: close all tabs!
        return QtGui.QMainWindow.close(self)

    def open_file(self, path):
        path = unicode(path)
        logging.debug('%s %s', 'Archive MainWindow.open_file', path)
        doc = filedata.MisuraDocument(path)
        tw = testwindow.TestWindow(doc)
        cw = self.centralWidget()
        win = cw.addTab(tw, tw.title)
        confdb.mem_file(path, tw.remote.measure['name'])
        cw.setCurrentIndex(cw.count() - 1)

    def open_database(self, path, new=False):
        idb = getDatabaseWidget(path, new=new)
        win = self.area.addSubWindow(idb)
        win.show()
        confdb.mem_database(path)
        self.connect(
            idb, QtCore.SIGNAL('selectedFile(QString)'), self.open_file)

    def new_database(self, path):
        self.open_database(path, new=True)

    def open_server(self, addr):
        idb = getRemoteDatabaseWidget(addr)
        if not idb:
            return False
        win = self.area.addSubWindow(idb)
        win.show()
        self.connect(
            idb, QtCore.SIGNAL('selectedRemoteUid(QString,QString)'), self.open_remote_uid)
        return True

    def open_remote_uid(self, addr, uid):
        addr = str(addr)
        uid = str(uid)
        path = addr + '|' + uid
        self.open_file(path)

    m3db = False

    def open_m3db(self, path):
        if self.m3db:
            self.m3db.hide()
            self.m3db.close()
            del self.m3db
        self.m3db = misura3.m3db.TestDialog(path=path)
        self.m3db.img = True
        self.m3db.keep_img = True
        self.m3db.force = False
        self.connect(
            self.m3db, QtCore.SIGNAL('select(QString)'), self.open_file)
        confdb.mem_m3database(path)
        self.m3db.show()

    def close_tab(self, idx):
        logging.debug('%s %s', 'Tab close requested', idx)
        if idx == 0:
            return
        w = self.tab.widget(idx)
        self.tab.removeTab(idx)
        # explicitly destroy the widget
        w.close()
        del w
