#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from .. import network, conf, _
from ..clientconf import confdb
from ..connection import LoginWindow, addrConnection
from ..confwidget import RecentMenu
from .. import parameters as params
from misura.client.helpmenu import HelpMenu

from PyQt4 import QtGui, QtCore
import functools


class MenuBar(QtGui.QMenuBar):

    """Main acquisition menus"""

    def __init__(self, server=False, parent=None):
        QtGui.QMenuBar.__init__(self, parent)
        self.remote = False
        self.server = server
        self.windows = {}
        self.objects = {}
        self.lstActions = []
        self.func = []
        if self.fixedDoc is False:
            self.set_acquisition_mode()
        else:
            self.set_browser_mode()
        self.measure = self.addMenu(_('Measure'))
        self.connect(
            self.measure, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
        self.settings = self.addMenu(_('Settings'))
        self.connect(
            self.settings, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
        if self.fixedDoc is False:
            self.measure.setEnabled(False)
            self.settings.setEnabled(False)

        self.help_menu = HelpMenu()
        self.help_menu.add_help_menu(self)

        if server is not False:
            self.setServer(server)

    @property
    def fixedDoc(self):
        if self.parent() is None:
            return False
        return self.parent().fixedDoc

    def set_acquisition_mode(self):
        self.connectTo = self.addMenu(_('Connect'))
        self.servers = RecentMenu(confdb, 'server', self)
        self.servers.setTitle('Server')
        self.connect(
            self.servers, QtCore.SIGNAL('select(QString)'), self.setAddr)
        self.connectTo.addMenu(self.servers)
        self.instruments = self.connectTo.addMenu('Instruments')
        self.instruments.setEnabled(False)
        self.actLogout = self.connectTo.addAction(_('Logout'), self.logout)
        self.actLogout.setEnabled(False)
        self.actShutdown = self.connectTo.addAction(
            _('Shutdown'), self.shutdown)
        self.actShutdown.setEnabled(False)
        self.actRestart = self.connectTo.addAction(_('Restart'), self.restart)
        self.actRestart.setEnabled(False)

    def set_browser_mode(self):
        self.connectTo = QtGui.QMenu()
        self.instruments = QtGui.QMenu()
        #       self.chooser.setView(self.tree)

    def setAddr(self, addr):
        addr = str(addr)
        obj = addrConnection(addr)
        if not obj:
            logging.debug('MenuBar.setAddr: Failed!')
            return
        network.setRemote(obj)

    def logout(self):
        if not self.server:
            return
        r = self.server.users.logout()
        confdb.logout(self.server.addr)
        msg = _('You have been logged out (%s): \n %r') % (self.server.user, r)
        QtGui.QMessageBox.information(self, _('Logged out'),msg)

    def shutdown(self):
        btn = QtGui.QMessageBox.warning(None, _('Confirm Shutdown'),
                          _('Do you really want to shutdown the instrument operative system?'), 
                          QtGui.QMessageBox.Cancel|QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)
        if btn != QtGui.QMessageBox.Ok:
            logging.debug('Shutdown request aborted')
            return False        
        status, msg = self.server.support['halt']
        if status!=0:
            QtGui.QMessageBox.warning(self, _('Shutdown request failed'), 
                                      _('Shutdown failed with the following error:\n {!r}').format((status, msg))
                                      )
            return False              
        msg = _('Server is shutting down.\nPlease close any client window and shutdown power interruptor in 30 seconds.\nReply: \n %r') % msg
        QtGui.QMessageBox.information(self, _('Shutting Down'), msg)
        return True

    def restart(self):
        QtGui.QMessageBox.information(self, _('Restart Down'),
                                      'Server is restarting:\n %r' % self.server.restart())

    def getConnection(self, srv):
        LoginWindow(srv.addr, srv.user, srv.password, parent=self).exec_()

    def setServer(self, server=False):
        self.instruments.clear()
        # INSTRUMENTS Submenu
        self.lstInstruments = []
        self.server = server
        if not server:
            self.server = network.manager.remote

        if self.fixedDoc:
            inslist = []
        else:
            inslist = self.server['instruments']
        for (title, name) in inslist:
            opt = 'eq_' + name
            if self.server.has_key(opt):
                if not self.server[opt]:
                    logging.debug('Disabled instrument', opt, self.server[opt])
                    continue
            elif not params.debug:
                logging.debug('Skipping unknown instrument', name)
                continue
            obj = getattr(self.server, name, False)
            if not obj:
                logging.debug('missing handler', name)
                continue
            f = functools.partial(self.parent().setInstrument, obj)
            act = self.instruments.addAction(
                '%s (%s)' % (title, obj['comment']), f)
            self.func.append(f)
            self.lstInstruments.append((act, title))
        self.appendGlobalConf()
        # Enable menu and menu items after server connection
        if self.fixedDoc is False:
            self.instruments.setEnabled(True)
            self.actLogout.setEnabled(True)
            self.actShutdown.setEnabled(True)
            self.actRestart.setEnabled(True)
            self.settings.setEnabled(True)
        logging.debug('lstInstruments', self.lstInstruments)

    def get_window(self, key):
        d = self.windows.get(key, False)
        if not d and self.objects.has_key(key):
            d = self.objects[key]()
            self.windows[key] = d
        elif not d:
            d = key
        return d

    def hideShow(self, key):
        d = self.get_window(key)
        if d.isVisible():
            d.hide()
        else:
            d.show()

    def setInstrument(self, remote, server=False):
        self.setServer(server)
        self.remote = remote
        self.lstActions = []
        parent = self.parent()
        name = self.remote['devpath']
        for act, aname in self.lstInstruments:
            if aname == name:
                act.setCheckable(True)
                act.setChecked(True)
                break
        # MEASURE Menu
        self.measure.clear()
        if not self.fixedDoc:
            self.measure.addAction(
                _('Initialize New Test'), self.parent().init_instrument)
            self.measure.addAction(
                _('Delayed start'), self.parent().delayed_start)
        # TODO: Share windows definitions with mainwin?
        self.windows['measureDock'] = parent.measureDock
        self.showMeasureDock = functools.partial(self.hideShow, 'measureDock')
        act = self.measure.addAction(
            _('Test Configuration'), self.showMeasureDock)
        self.lstActions.append((act, 'measureDock'))

        self.windows['snapshotsDock'] = parent.snapshotsDock
        self.showSnapshotsStrip = functools.partial(
            self.hideShow, 'snapshotsDock')
        act = self.measure.addAction(_('Storyboard'), self.showSnapshotsStrip)
        self.lstActions.append((act, 'snapshotsDock'))

        self.windows['graphWin'] = parent.graphWin
        self.showGraph = functools.partial(self.hideShow, 'graphWin')
        act = self.measure.addAction(_('Data Plot'), self.showGraph)
        self.lstActions.append((act, 'graphWin'))

        self.windows['tableWin'] = parent.tableWin
        self.showTable = functools.partial(self.hideShow, 'tableWin')
        act = self.measure.addAction(_('Data Table'), self.showTable)
        self.lstActions.append((act, 'tableWin'))

        self.windows['logDock'] = parent.logDock
        self.showLogWindow = functools.partial(self.hideShow, 'logDock')
        act = self.measure.addAction(_('Log Window'), self.showLogWindow)
        self.lstActions.append((act, 'logDock'))

        self.measure.addAction(_('Reload data'), self.reload_data)

        if self.fixedDoc:
            self.measure.addSeparator()
            self.measure.addAction(_('Save to file'))
            self.measure.addAction(_('Close'))
        else:
            self.measure.addAction(_('Quit Client'))
        self.measure.setEnabled(True)

        # SETTINGS Menu
        self.settings.clear()
        self.showInstrumentConf = functools.partial(self.hideShow, 'iconf')
        act = self.settings.addAction(_('Instrument'), self.showInstrumentConf)
#       self.objects['iconf']=functools.partial(conf.Interface, self.server,  self.remote)
        self.objects['iconf'] = functools.partial(
            conf.TreePanel, self.remote, None, self.remote)
        self.lstActions.append((act, self.remote))

        # DEVICES SubMenu
        self.devices = self.settings.addMenu(_('Devices'))
        self.connect(
            self.devices, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
        paths = self.remote['devices']

        for path in paths:
            role, path = path
            lst = self.server.searchPath(path)
            if lst is False:
                logging.debug('Undefined path for role', role, path)
                continue
            obj = self.server.toPath(lst)
            if obj is None:
                logging.debug('Path not found')
                continue
            self.addDevConf(obj, role)
        self.appendGlobalConf()

        for act, cf in self.lstActions:
            act.setCheckable(True)

    def appendGlobalConf(self):
        self.objects['mconf'] = functools.partial(conf.MConf, self.server)
        self.showMConf = functools.partial(self.hideShow, 'mconf')
        act = self.settings.addAction(_('Global'), self.showMConf)
        act.setCheckable(True)
        self.lstActions.append((act, 'mconf'))

    def addDevConf(self, obj, role):
        #       self.objects[obj]=functools.partial(conf.Interface, self.server, obj)
        self.objects[obj] = functools.partial(conf.TreePanel, obj, None, obj)
        f = functools.partial(self.hideShow, obj)
        act = self.devices.addAction('%s (%s)' % (role, obj['name']), f)
        self.lstActions.append((act, obj))

    def updateActions(self):
        for act, key in self.lstActions:
            conf = self.windows.get(key, False)
            if not conf:
                continue
            conf = self.get_window(key)
            if not conf:
                continue
            if type(conf) == type(''):
                continue
            if hasattr(conf, '_Method__name'):
                continue
            logging.debug('Updating', conf)
            act.setChecked(conf.isVisible())

    def reload_data(self):
        self.parent().uid = False
        self.parent().resetFileProxy()
