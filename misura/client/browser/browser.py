#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore
import os

from misura.client import configure_logger
from misura.canon.plugin import dataimport

from .. import _
from .. import confwidget
from .. import filedata
from ..clientconf import confdb
from .. import iutils
from .. import widgets
from ..database import getDatabaseWidget, getRemoteDatabaseWidget
from .. import parameters

from . import menubar
from . import testwindow

from traceback import print_exc

try:
    from .. import misura3
except:
    print_exc()
    misura3 = False


class DatabasesArea(QtGui.QMdiArea):
    convert = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super(DatabasesArea, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        logging.debug('%s %s', 'dragEnterEvent', event.mimeData())
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, drop_event):
        urls = drop_event.mimeData().urls()
        for url in urls:
            url = url.toString().replace('file://','')
            # on windows, remove also the first "/"
            if os.name.lower()=='nt':
                url = url[1:]
            self.convert.emit(url)


class MainWindow(QtGui.QMainWindow):

    """Open single files, local databases, remote databases."""

    def __init__(self, parent=None):
        super(QtGui.QMainWindow, self).__init__(parent)
        configure_logger('browser.log')
        self.tab = QtGui.QTabWidget()
        self.setAcceptDrops(True)
        self.area = DatabasesArea(self)
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

        self.connect(self.myMenuBar.recentFile, QtCore.SIGNAL(
            'convert(QString)'), self.convert_file)

        self.area.convert.connect(self.convert_file)

        self.connect(self.myMenuBar.recentDatabase, QtCore.SIGNAL(
            'select(QString)'), self.open_database)
        self.connect(self.myMenuBar, QtCore.SIGNAL(
            'new_database(QString)'), self.new_database)

        # Recent objects greeter window:
        greeter = confwidget.Greeter(parent=self)
        self.connect(greeter.file, greeter.file.sig_select, self.open_file)
        self.connect(greeter.file, greeter.file.sig_convert, self.convert_file)
        self.connect(
            greeter.database, greeter.database.sig_select, self.open_database)

        if confdb['m3_enable'] and misura3:
            self.connect(
                greeter.m3database, greeter.database.sig_select, self.open_m3db)
            self.connect(self.myMenuBar.recentM3db, QtCore.SIGNAL(
                'select(QString)'), self.open_m3db)

        win = self.area.addSubWindow(greeter,
                                     QtCore.Qt.CustomizeWindowHint |
                                     QtCore.Qt.WindowTitleHint |
                                     QtCore.Qt.WindowMinMaxButtonsHint)

        self.setWindowIcon(QtGui.QIcon(os.path.join(parameters.pathArt, 'icon.svg')))

    def closeEvent(self, event):
        iutils.app.quit()

    def convert_file(self, path):
        if path.endswith('.h5'):
            self.open_file(path)
            return True
        self.converter = False
        self.converter = dataimport.get_converter(path)
        run = widgets.RunMethod(self.converter.convert, path, filedata.jobs, filedata.job, filedata.done)
        run.step = 100
        run.pid = self.converter.pid
        self.connect(run.notifier, QtCore.SIGNAL('done()'), self._open_converted, QtCore.Qt.QueuedConnection)
        self.connect(run.notifier, QtCore.SIGNAL('failed(QString)'), self._failed_conversion, QtCore.Qt.QueuedConnection)
        QtCore.QThreadPool.globalInstance().start(run)
        return True

    def _open_converted(self):
        self.open_file(self.converter.outpath)

    def _failed_conversion(self, error):
        QtGui.QMessageBox.warning(self, _("Failed conversion"), error)

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
        self.tab.tabBar().tabButton(
            tab_index, QtGui.QTabBar.RightSide).resize(0, 0)
