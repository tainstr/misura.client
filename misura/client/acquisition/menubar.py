#!/usr/bin/python
# -*- coding: utf-8 -*-
import os 
import functools

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from .. import network, conf, _
from ..clientconf import confdb
from ..connection import LoginWindow, addrConnection
from ..confwidget import RecentMenu
from .. import parameters as params
from misura.client.helpmenu import HelpMenu
from . import windows
from .. import iniconf
from .. import widgets
from PyQt4 import QtGui, QtCore



class MenuBar(QtGui.QMenuBar):

    """Main acquisition menus"""
    quitClient = QtCore.pyqtSignal()
    
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
        self.view_menu = self.addMenu(_('View'))
        self.connect(
            self.view_menu, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
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
            _('Shutdown electronics'), self.shutdown)
        self.actShutdown.setEnabled(False)
        self.actRestart = self.connectTo.addAction(_('Restart Server'), self.restart)
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
        LoginWindow(srv.addr, srv.user, srv.password, srv.mac, parent=self).exec_()
        

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
            if name == 'kiln' and self.server._readLevel<4:
                continue
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
            f = functools.partial(self.parent().setInstrument, obj, preset=name)
            icon = QtGui.QIcon(os.path.join(params.pathArt, 'small_' + name + '.svg'))
            act = self.instruments.addAction(icon, title.capitalize(), f)
            self.func.append(f)
            self.lstInstruments.append((act, title))

            presets = filter(lambda preset: preset not in ['default', 'factory_default'], obj.listPresets())
            for preset in presets:
                f = functools.partial(self.parent().setInstrument, preset=preset, remote=obj)
                name = ' '.join(preset.split('_'))
                icon = QtGui.QIcon(os.path.join(params.pathArt, 'small_' + name + '.svg'))
                act = self.instruments.addAction(icon, name.capitalize(), f)
                self.func.append(f)
                self.lstInstruments.append((act, name))


        self.appendGlobalConf()
        # Enable menu and menu items after server connection
        if self.fixedDoc is False:
            self.instruments.setEnabled(True)
            self.actLogout.setEnabled(True)
            self.actShutdown.setEnabled(True)
            self.actRestart.setEnabled(True)
            self.settings.setEnabled(True)
        logging.debug('lstInstruments', self.lstInstruments)
        if self.server._readLevel<4:
            self.removeAction(self.settings.menuAction())
            self.settings.setEnabled(False)
            

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

        self.arrange_windows()

    def arrange_windows(self):
        windows.arrange(self.parent().centralWidget(), self.parent().name)
        
    def clear_windows(self):
        """Closes all configuration-dependent windows"""
        for key, w in self.windows.items():
            if not isinstance(w, conf.TreePanel) and not isinstance(w, conf.MConf):
                continue
            w.close()
            w.hide()
            self.windows.pop(key)
            
    def add_view_plotboard(self):
        if self.parent().plotboardDock is False:
            return False
        self.windows['plotboardDock'] = self.parent().plotboardDock
        self.showPlotBoardWindow = functools.partial(self.hideShow, 'plotboardDock')
        act = self.view_menu.addAction(_('Plots Board Window'), self.showPlotBoardWindow)
        act.setCheckable(True)
        act.setChecked(self.parent().plotboardDock.isVisible())
        self.lstActions.append((act, 'plotboardDock'))     
        return True      

    def setInstrument(self, remote, server):
        self.clear_windows()
        self.setServer(server)
        self.remote = remote
        self.lstActions = []
        preset = self.remote['preset']
        parent = self.parent()
        name = self.remote['devpath']
        name_from_preset = ' '.join(preset.split('_'))

        for act, aname in self.lstInstruments:
            if aname == name and preset in ['default', 'factory_default'] or aname == name_from_preset:
                act.setCheckable(True)
                act.setChecked(True)

        self.measure.clear()
        if not self.fixedDoc:
            self.measure.addAction(
                _('Repeat initialization'), self.parent().init_instrument)
            self.measure.addAction(
                _('Delayed start'), self.parent().delayed_start)
        # TODO: Share windows definitions with mainwin?
        self.windows['measureDock'] = parent.measureDock
        self.showMeasureDock = functools.partial(self.hideShow, 'measureDock')
        act = self.view_menu.addAction(_('Arrange Windows'), self.arrange_windows)
        act.setChecked(False)
        act.setCheckable(False)

        act = self.view_menu.addAction(
            _('Test Configuration'), self.showMeasureDock)
        self.lstActions.append((act, 'measureDock'))

        self.windows['snapshotsDock'] = parent.snapshotsDock
        self.showSnapshotsStrip = functools.partial(
            self.hideShow, 'snapshotsDock')
        act = self.view_menu.addAction(_('Storyboard'), self.showSnapshotsStrip)
        self.lstActions.append((act, 'snapshotsDock'))

        self.windows['graphWin'] = parent.graphWin
        self.showGraph = functools.partial(self.hideShow, 'graphWin')
        act = self.view_menu.addAction(_('Data Plot'), self.showGraph)
        self.lstActions.append((act, 'graphWin'))

        self.windows['tableWin'] = parent.tableWin
        self.showTable = functools.partial(self.hideShow, 'tableWin')
        act = self.view_menu.addAction(_('Data Table'), self.showTable)
        self.lstActions.append((act, 'tableWin'))

        self.windows['logDock'] = parent.logDock
        self.showLogWindow = functools.partial(self.hideShow, 'logDock')
        act = self.view_menu.addAction(_('Log Window'), self.showLogWindow)
        self.lstActions.append((act, 'logDock'))
        
        self.add_view_plotboard()

        self.measure.addAction(_('Reload data'), self.reload_data)

        if self.fixedDoc:
            self.measure.addSeparator()
            self.measure.addAction(_('Close'), self.quit)
        else:
            self.measure.addAction(_('Quit Client'), self.quit)
        self.measure.setEnabled(True)

        # SETTINGS Menu
        self.settings.clear()
        self.showInstrumentConf = functools.partial(self.hideShow, 'iconf')
        if self.server._readLevel>=4:
            act = self.settings.addAction(_('Instrument'), self.showInstrumentConf)
            self.objects['iconf'] = functools.partial(
                conf.TreePanel, self.remote, None, self.remote)
            self.lstActions.append((act, self.remote))

            # DEVICES SubMenu
            self.devices = self.settings.addMenu(_('Devices'))
            self.connect(
                self.devices, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
        
            #FIXME: devices are empty in browser!
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
            
    def quit(self):
        print 'QUIT'
        self.quitClient.emit()

    def appendGlobalConf(self):
        self.settings.addAction(_('Export configuration'), self.export_configuration)
        if self.server._readLevel<4:
            return 
        if self.server and not self.fixedDoc:
            self.settings.addAction(_('Import configuration'), self.import_configuration)
            self.settings.addAction(_('Send update package'), self.update_server)
            self.settings.addAction(_('Verify all motor limits'), self.check_motor_limits)
        self.objects['mconf'] = functools.partial(conf.MConf, self.server)
        self.showMConf = functools.partial(self.hideShow, 'mconf')
        act = self.settings.addAction(_('Global'), self.showMConf)
        act.setCheckable(True)
        self.lstActions.append((act, 'mconf'))
        
           
    def export_configuration(self):
        iniconf.export_configuration(self.server, self)
        
    def import_configuration(self):
        iniconf.import_configuration(self.server, self)

    def addDevConf(self, obj, role):
        if self.server._readLevel<4:
            return False
        self.objects[obj] = functools.partial(conf.TreePanel, obj, None, obj)
        f = functools.partial(self.hideShow, obj)
        act = self.devices.addAction('%s (%s)' % (role, obj['name']), f)
        self.lstActions.append((act, obj))
        return True

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
        
    def update_server(self):
        self.pkg = widgets.aFileList(self.server, self.server.support, 
                          self.server.support.gete('packages'), parent=self)
        self.pkg.hide()
        if self.pkg.send(): 
            self.pkg.transfer.dlFinished.connect(self._apply_update_server)
        
    def _apply_update_server(self, *a):
        self.server.support['packages'] = os.path.basename(self.pkg.transfer.outfile)
        logging.info('Apply server update', self.server.support['packages'], self.pkg.transfer.outfile)
        
        btn = widgets.aButton(self.server, self.server.support,
                                self.server.support.gete('applyExe'), parent=self)
        btn.hide()
        btn.get()
        btn.show_msg()
        self.server.restart()
        logging.debug('Closing the client while server restarts.')
        self.quit()
        
    def check_motor_limits(self):
        from .. import autoconf
        w = autoconf.FirstSetupWizard(self.server)
        w.read_serials()
        return
        r = widgets.RunMethod(w.configure_limits)
        r.pid = 'Checking motor limits'
        r.abort = w.abort
        r.do()
        
        self._motor_limits_check = r
        
        
        

