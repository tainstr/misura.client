#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore
from .. import _
from .. import confwidget
from .. import filedata
from .. import misura3
from ..clientconf import confdb
from .. import iutils
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
        self.tab.setTabsClosable(True)
        self.tab.setDocumentMode(True)
        database_tab_index = 0
        self.remove_close_button_from_tab(database_tab_index)
        self.setCentralWidget(self.tab)
        self.setMinimumSize(800, 600)
        self.setWindowTitle(_('Misura Browser'))
        self.myMenuBar = menubar.BrowserMenuBar(parent=self)
        self.setMenuWidget(self.myMenuBar)

        self.connect(
            self.tab, QtCore.SIGNAL('tabCloseRequested(int)'), self.close_tab)

        self.connect(self.myMenuBar.recentFile, QtCore.SIGNAL(
            'select(QString)'), self.open_file)

        self.connect(self.myMenuBar.recentDatabase, QtCore.SIGNAL(
            'select(QString)'), self.open_database)
        self.connect(self.myMenuBar, QtCore.SIGNAL(
            'new_database(QString)'), self.new_database)



        # Recent objects greeter window:
        greeter = confwidget.Greeter(parent=self)
        self.connect(greeter.file, greeter.file.sig_select, self.open_file)
        self.connect(
            greeter.database, greeter.database.sig_select, self.open_database)

        if confdb['m3_enable']:
            self.connect(greeter.m3database, greeter.database.sig_select, self.open_m3db)
            self.connect(self.myMenuBar.recentM3db, QtCore.SIGNAL(
            'select(QString)'), self.open_m3db)

        win = self.area.addSubWindow(greeter)
        win.show()

    def closeEvent(self, event):
        iutils.app.quit()

    def open_file(self, path):
        path = unicode(path)
        logging.debug('%s %s', 'Browser MainWindow.open_file', path)
        try:
            doc = filedata.MisuraDocument(path)
        except Exception as error:
            self.myMenuBar.recentFile.conf.rem_file(path)
            QtGui.QMessageBox.warning(self, 'Error', str(error))
            return False

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


    def open_m3db(self, path):
        m3db = misura3.TestDialog(path=path)
        m3db.img = True
        m3db.keep_img = True
        m3db.force = False
        self.connect(
            m3db, QtCore.SIGNAL('select(QString)'), self.open_file)
        confdb.mem_m3database(path)
        win = self.area.addSubWindow(m3db)
        win.show()

    def close_tab(self, idx):
        logging.debug('%s %s', 'Tab close requested', idx)
        if idx == 0:
            return
        w = self.tab.widget(idx)
        self.tab.removeTab(idx)
        # explicitly destroy the widget
        w.close()
        del w

    def remove_close_button_from_tab(self, tab_index):
        self.tab.tabBar().tabButton(tab_index, QtGui.QTabBar.RightSide).resize(0,0)
