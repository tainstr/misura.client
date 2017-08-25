#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Configuration interface for misura.
Global instrument parametrization and setup."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import constructor
from devtree import ServerView
from .. import _
from .. import network
from ..live import registry
from ..clientconf import confdb
from ..connection import ServerSelector, ConnectionStatus, addrConnection
from ..confwidget import ClientConf, RecentMenu

from PyQt4 import QtGui, QtCore

class TreePanel(QtGui.QSplitter):

    def __init__(self, server=False, parent=None, select=False):
        QtGui.QSplitter.__init__(self, parent)
        self.remote = server
        self.server = server.root
        self.view = ServerView(server, parent=self)
        self.addWidget(self.view)
        self.tab = QtGui.QTabWidget(self)
        self.tab.setTabsClosable(True)
        self.tab.setDocumentMode(True)
        self.addWidget(self.tab)
        self.connect(
            self.view, QtCore.SIGNAL('activated(QModelIndex)'), self.select)
        self.connect(
            self.view, QtCore.SIGNAL('objTable(QModelIndex)'), self.objTable)
        self.connect(
            self.view, QtCore.SIGNAL('presetsTable(QModelIndex)'), self.presetsTable)
        self.connect(
            self.view, QtCore.SIGNAL('wiringGraph(QModelIndex)'), self.wiringGraph)
        self.connect(
            self.view, QtCore.SIGNAL('objNewTab(QModelIndex)'), self.objNewTab)
        self.connect(
            self.tab, QtCore.SIGNAL('tabCloseRequested(int)'), self.closeTab)
        self.setSizes([20, 80])
        self.setHandleWidth(10)
        if select is not False:
            self.select_remote(select)
        logging.debug('TreePanel.__init__', self.server, self.remote)

    def objTable(self):
        self.tab.currentWidget().show_details()
        
    def presetsTable(self):
        self.tab.currentWidget().presets_table()
        
    def wiringGraph(self):
        self.tab.currentWidget().wiring_graph()

    def objNewTab(self, index):
        """Opens in a new tab"""
        self.select(index, keepCurrent=True)

    def closeTab(self, i):
        """Closing action"""
        page = self.tab.widget(i)
        self.tab.removeTab(i)
        page.hide()
        page.deleteLater()
#		page.close()
#		del page

    def setPage(self, widget, title=False, keepCurrent=False):
        if not title:
            title = ''
        current = self.tab.currentIndex()
        if current >= 0 and not keepCurrent:
            logging.debug('Removing current tab')
            self.tab.currentWidget().close()
            self.closeTab(current)
        elif current < 0:
            current = 0
        logging.debug('Inserting tab', current)
        i = self.tab.insertTab(current, widget, title)
        self.tab.setTabToolTip(i, widget.name)
        logging.debug('Setting current index', i)
        self.tab.setCurrentIndex(i)

    def select(self, index, keepCurrent=False):
        model = self.view.model()
        node = model.data(index, role=-1)
        path = node.path
        logging.debug('selecting remote path', path)
        obj = self.remote.toPath(path)
        logging.debug('found object', obj)
        self.select_remote(obj, keepCurrent)

    def select_remote(self, obj, keepCurrent=False):
        logging.debug("select_remote obj", obj, obj.parent())
        logging.debug('mro', obj['mro'])
        path = obj['fullpath'].replace('MAINSERVER', 'server').split('/')
        if len(path) == 0:
            path = [self.remote['devpath']]
            obj = self.remote
        # Intercept device controllers:
        mro = obj['mro']
        if 'Camera' in mro:
            from misura.client import beholder
            page = beholder.CameraController(self.server, obj, parent=self)
        # Otherwise, generic Interface:
        else:
            page = constructor.Interface(
                self.server, obj, obj.describe(), parent=self)
        logging.debug("constructor", page, path[-1])
        self.setPage(page, '/'.join(path), keepCurrent=keepCurrent)
        logging.debug("page ok")


class MConf(QtGui.QMainWindow):
    tree = False
    fixed_path = False

    def __init__(self, server=False, fixed_path=False, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle(_('Misura Configuration Panel'))
        self.setGeometry(100, 100, 800, 600)
        self.tab = QtGui.QTabWidget(self)
        self.setCentralWidget(self.tab)
        self.server = server
        self.fixed_path = fixed_path
        self.menu = RecentMenu(confdb, 'server', parent=self)
        self.menu.setTitle('Server')
        self.connect(self.menu, QtCore.SIGNAL(
            'server_disconnect()'), self.server_disconnect)
        self.connect(
            self.menu, QtCore.SIGNAL('server_shutdown()'), self.server_shutdown)
        self.connect(
            self.menu, QtCore.SIGNAL('server_restart()'), self.server_restart)
        self.connect(self.menu, QtCore.SIGNAL('select(QString)'), self.setAddr)
        self.cmenu = QtGui.QMenu('Client')
        self.cmenu.addAction(_('Configuration'), self.clientConf)
        self.cmenu.addAction(_('Pending Tasks'), self.show_tasks)
        self.menuBar().addMenu(self.menu)
        self.menuBar().addMenu(self.cmenu)
        self.connect(
            network.manager, QtCore.SIGNAL('connected()'), self.resetServer)
        if not server:
            self.getIP()
        else:
            self.redraw()

    def getIP(self):
        ss = ServerSelector(self.menu)
        self.connect(network.manager, QtCore.SIGNAL('connected()'), ss.close)
        self.tab.addTab(ss, _('Server Selection'))
        self.tab.setCurrentIndex(self.tab.count() - 1)
        self.tab.addTab(ConnectionStatus(self), _('Current Connection Status'))
        self.server = network.manager.remote

    def setAddr(self, addr):
        addr = str(addr)
        obj = addrConnection(addr)
        if not obj:
            logging.debug('MConf.setAddr: Connection to address failed')
            return
        network.setRemote(obj)

    def server_disconnect(self):
        network.manager.remote.disconnect()

    def server_shutdown(self):
        self.server.shutdown()

    def server_restart(self):
        self.server.shutdown(0, 1)

    def resetServer(self):
        self.server = network.manager.remote
        if self.fixed_path:
            self.server = network.manager.remote.toPath(self.fixed_path)
        self.redraw()

    def redraw(self):
        self.tab.removeTab(2)
        if self.tree:
            self.tree.close()
            del self.tree
        self.tree = TreePanel(self.server, parent=self)
        logging.debug(self.tree.view.model().item.children)
        self.tab.addTab(self.tree, _("Tree Panel"))
        self.tab.setCurrentIndex(2)

    def clientConf(self):
        self.cc = ClientConf()
        self.cc.show()

    def show_tasks(self):
        registry.taskswg.user_show = True
        registry.taskswg.show()
