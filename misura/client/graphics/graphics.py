#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Applicazione di grafica basata su Veusz"""
# Librerie generali
import os
from misura.canon.logger import Log as logging
import sip
sip.setapi('QString', 2)
from PyQt4 import QtGui, QtCore
# Veusz libraries
import veusz.utils
from veusz.windows.mainwindow import MainWindow
import veusz.document as document

import veusz.setting as setting
from veusz import veusz_main

from .. import _
from .. import misura3
from .. import filedata
from .. import plugin
from .. import parameters as params
from ..plugin import *  # ??? devo importarlo per pyinstaller...!
from .. import navigator
from ..clientconf import confdb
from ..database import getDatabaseWidget, getRemoteDatabaseWidget
import veuszplot
from ..confwidget import RecentMenu, ClientConf
from misura.client import iutils

setting.transient_settings['unsafe_mode'] = True




class CustomInterface(object):

    def __init__(self, mainwindow, name):
        self.mw = mainwindow
        self.menu = self.mw.menuBar().addMenu(name)
        self.name = name
#       imp='Import'+name
#       self.mw.ci.addCommand(imp, self.open_file)
#       self.mw.document.eval_context[imp]=self.open_file

    def buildMenus(self, actions):
        # Build menus
        menu = actions.keys()
        mmenus = [[self.name.lower(), '&' + self.name, menu]]
        veusz.utils.constructMenus(
            self.mw.menuBar(), {self.name.lower(): self.menu}, mmenus, actions)

    def buildToolbars(self, actions):
        # Build the toolbars
        tb = QtGui.QToolBar(self.name + " Toolbar", self.mw)
        tb.setObjectName(self.name + 'Toolbar')
        self.mw.addToolBar(QtCore.Qt.TopToolBarArea, tb)
        veusz.utils.addToolbarActions(tb, actions, tuple(actions.keys()))


def misura_import(self, filename, **options):
    """Import misura data from HDF file"""
    defaults = {'rule_exc': confdb['rule_exc'],
                'rule_inc': confdb['rule_inc'],
                'rule_load': confdb['rule_load'] + '\n' + confdb['rule_plot'],
                'rule_unit': confdb['rule_unit']}
    for k, v in defaults.iteritems():
        if options.has_key(k): continue
        options[k] = v
    # lookup filename
    filename = unicode(filename)
    realfilename = self.findFileOnImportPath(filename)
    logging.debug('%s %s %s', 'open_file:', filename, realfilename)
    print 'misura_import with params', options
    p = filedata.ImportParamsMisura(filename=realfilename, version=-1, **options)
    op = filedata.OperationMisuraImport(p)

    self.document.applyOperation(op)
    confdb.mem_file(realfilename, op.measurename)
    dsnames = op.outdatasets
    logging.debug('Imported datasets %s' % (' '.join(dsnames), ))
    return dsnames

# Add the ImportMisura command to the CommandInterface class
imp = 'ImportMisura'
safe = list(document.CommandInterface.safe_commands)
safe.append(imp)
document.CommandInterface.safe_commands = safe
document.CommandInterface.ImportMisura = misura_import

def set_data_val(self, dsname, column, row, val):
    """Set dataset `dsname` to `val` in range `row`. row can be a slice in case val is array."""
    op = document.OperationDatasetSetVal(dsname, column, row, val)
    self.document.applyOperation(op)

# Add the SetDataVal command to the CommandInterface class
imp = 'SetDataVal'
safe = list(document.CommandInterface.safe_commands)
safe.append(imp)
document.CommandInterface.safe_commands = safe
document.CommandInterface.SetDataVal = set_data_val

def set_data_attr(self, dsname, attrname, val):
    """Set dataset attribute `attrname` to `val`"""
    ds = self.document.data[dsname]
    setattr(ds, attrname, val)
    print 'setting attr',dsname,attrname,val
    op = document.OperationDatasetSet(dsname, ds)
    self.document.applyOperation(op)

# Add the SetDataAttr command to the CommandInterface class
imp = 'SetDataAttr'
safe = list(document.CommandInterface.safe_commands)
safe.append(imp)
document.CommandInterface.safe_commands = safe
document.CommandInterface.SetDataAttr = set_data_attr

class MisuraInterface(CustomInterface, QtCore.QObject):

    """MainWindow methods useful for misura specific widgets and actions"""

    def __init__(self, mainwindow):
        CustomInterface.__init__(self, mainwindow, 'Misura')
        QtCore.QObject.__init__(self, parent=mainwindow)

        # Navigator
        self.openedFilesDock = QtGui.QDockWidget(self.mw.centralWidget())
        self.openedFilesDock.setWindowTitle(_('Misura Navigator'))
        self.openedFiles = navigator.Navigator(
            parent=self.openedFilesDock, doc=self.mw.document,  mainwindow=self.mw)
        self.openedFilesDock.setWidget(self.openedFiles)
        self.openedFilesDock.setObjectName('misuranavigator')
        self.mw.addDockWidget(
            QtCore.Qt.RightDockWidgetArea, self.openedFilesDock)

        self.mw.plot.sigUpdatePage.connect(self.update_page)
#       self.connect(self.mw.plot,QtCore.SIGNAL("sigUpdatePage"),self.update_page)
        self.connect(
            self.openedFiles, QtCore.SIGNAL("select(QString)"), self.nav_select)

        # Recent Files Menus
        self.recentFile = RecentMenu(confdb, 'file', self.mw)
        self.connect(
            self.recentFile, QtCore.SIGNAL('select(QString)'), self.liveImport)
        self.menu.addMenu(self.recentFile)
        self.recentDatabase = RecentMenu(confdb, 'database', self.mw)
        self.connect(self.recentDatabase, QtCore.SIGNAL(
            'select(QString)'), self.open_database)
        self.menu.addMenu(self.recentDatabase)
#        self.recentServer = RecentMenu(confdb, 'server', self.mw)
#        self.connect(self.recentServer, QtCore.SIGNAL(
#            'select(QString)'), self.open_server)
#        self.menu.addMenu(self.recentServer)

#        ACTIONS
        a = veusz.utils.makeAction
        self.actions = {
#                        'm4.connect':
#                            a(self, 'Connect to a misura server', 'Connect',
#                          self.recentServer.new, icon='m4.connect'),
                        'm4.open':
                        a(self, 'Open Local Test File', 'Open File',
                          self.recentFile.new, icon='m4.open'),
                        'm4.nav':
                        a(self, 'Navigator', 'Opened Tests Navigator',
                          self.hs_navigator, icon='m4.open'),
                        'm4.conf':
                        a(self, 'Preferences', 'Preferences',
                          self.open_conf, icon='m4.conf'),

                        }

        def slotfn(klass):
            return lambda: self.mw.treeedit.slotMakeWidgetButton(klass)
        #TODO: Find better place for those!
        for widgettype in []:#  ('datapoint', 'intercept', 'synaxis', 'imagereference'):
            wc = document.thefactory.getWidgetClass(widgettype)
            slot = slotfn(wc)
            self.mw.treeedit.addslots[wc] = slot
            actionname = 'add.' + widgettype
            self.actions[actionname] = veusz.utils.makeAction(
                self.mw.treeedit,
                wc.description, 'Add %s' % widgettype,
                slot,
                icon='button_%s' % widgettype)
        self.mw.treeedit.vzactions.update(self.actions)
        self.buildMenus(self.actions)
        self.buildToolbars(self.actions)

        self.mw.ci.addCommand('DefaultPlot', self.defaultPlot)

    def open_conf(self):
        self.cc = ClientConf()
        self.cc.show()

    def update_page(self, *foo):
        """Update the navigator view in order to show colours and styles
        effectively present in the current page"""
        n = self.mw.plot.getPageNumber()
        page = self.mw.document.basewidget.getPage(n)
        if page is None:
            logging.debug('%s %s', 'NO PAGE FOUND', n)
            return
        if self.openedFiles.model().page.startswith(page.path):
            logging.debug('Not updating page %s', page.path)
            return
        logging.debug('MisuraInterface.update_page', self.openedFiles.model().page, page.path)
        self.openedFiles.model().set_page(page.path)
        logging.debug('%s', 'done model.set_page')
        self.connect(
            self.mw.plot, QtCore.SIGNAL("sigUpdatePage"), self.update_page)



    def nav_select(self, path):
        """Collect selection signals from the navigators and route them to the widgets tree"""
        view = self.mw.treeedit.treeview
        model = view.model()
        wdg = self.mw.document.resolveFullWidgetPath(path)
        idx = model.getWidgetIndex(wdg)
        view.setCurrentIndex(idx)

    def hs_navigator(self):
        """Hide/show the Misura Navigator for opened tests and files"""
        if self.openedFilesDock.isVisible():
            self.openedFilesDock.hide()
        else:
            self.openedFilesDock.show()

    def open_database(self, path):
        idb = getDatabaseWidget(path)
        if not idb:
            return False
        idb.show()
        self.connect(
            idb, QtCore.SIGNAL('selectedFile(QString)'), self.liveImport)
        # Keep a reference
        self.idb = idb

    def open_server(self, path):
        idb = getRemoteDatabaseWidget(path)
        if not idb:
            return False
        idb.show()

    def listImport(self):
        """Import data from a list of misura HDF files."""
        if not getattr(self, 'imd', False):
            return
        for f in self.imd.ls:
            f = str(f)
            self.liveImport(f, options=self.imd.options)
        self.imd.close()

    def defaultPlot(self, dsn):
        p = plugin.DefaultPlotPlugin()
        p.apply(self.mw.cmd, {'dsn': dsn})

    def liveImport(self, filename, options={}):
        """Import misura data and do the default plotting"""
        self.mw.document.suspendUpdates()
        dsn = self.open_file(filename, **options)
        self.defaultPlot(dsn)
        self.mw.document.enableUpdates()
        self.mw.plot.actionForceUpdate()
        self.openedFiles.refresh_model()

    def open_file(self, filename,  **options):
        """Import misura data from HDF file"""
        # lookup filename
        filename = unicode(filename)
        print 'importing misura with defaults'
        dsnames = self.mw.cmd.ImportMisura(filename, **options)
        self.openedFiles.refresh_model()
        return dsnames


class Misura3Interface(CustomInterface, QtCore.QObject):

    """MainWindow methods useful for Misura3 specific widgets and actions"""

    def __init__(self, mainwindow):
        CustomInterface.__init__(self, mainwindow, 'Misura3')
        QtCore.QObject.__init__(self, parent=mainwindow)

        self.recentDatabase = RecentMenu(confdb, 'm3database', self.mw)
        self.connect(self.recentDatabase, QtCore.SIGNAL(
            'select(QString)'), self.open_database)
        self.menu.addMenu(self.recentDatabase)

    m3db = False
    def open_database(self, path):
        if self.m3db:
            self.m3db.hide()
            self.m3db.close()
            self.m3db = False
        db = misura3.TestDialog(path=path)
        db.keep_img = True
        db.img = True
        db.force = False
        self.connect(db, QtCore.SIGNAL('select(QString)'), self.liveImport)
        confdb.mem_m3database(path)
        db.show()
        self.m3db = db

    def liveImport(self, filename):
        """Import and plot default datasets. Called upon user request"""
        self.mw.document.suspendUpdates()
        dsn = self.open_file(filename)
        p = plugin.DefaultPlotPlugin()
        p.apply(self.mw.cmd, {'dsn': dsn})
        self.mw.document.enableUpdates()
        self.mw.plot.actionForceUpdate()
        self.mw.m4.openedFiles.refresh_model()

    def open_file(self, filename, **options):
        """Import misura data from HDF file"""
        # lookup filename
        filename = unicode(filename)
        dsnames = self.mw.cmd.ImportMisura(filename, **options)
        return dsnames


from misura.client.filedata import MisuraDocument


class Graphics(MainWindow):

    """Main Graphics window, derived directly from Veusz"""
    # FIXME: patch to Veusz for dynamic document substitution!
    @property
    def document(self):
        return self._document

    @document.setter
    def document(self, ndoc):
        """Block overwrites! (hack!)"""
        return

    def __init__(self, *a):
        iutils.loadIcons()
        logging.debug('%s', 'Load Icons OK')
        self._document = MisuraDocument()
        # Shortcuts to command interpreter and interface
        MainWindow.__init__(self, *a)
        logging.debug('%s', 'MainWindow init')
        self.ci = self.console.interpreter
        self.cmd = self.ci.interface
        # misura Interface
        logging.debug('%s', 'misura Interface')
        self.m4 = MisuraInterface(self)
        # Misura3 Interface
        # print 'Misura3 Interface'
        self.m3 = Misura3Interface(self)
        self.datadock.hide()

    def setupDefaultDoc(self):
        """Make default temperature/time pages"""
        plugin.makeDefaultDoc(self.cmd, title=True)
        self.loadDefaultStylesheet()
        self.loadDefaultCustomDefinitions()


class GraphicsApp(veusz_main.VeuszApp):

    def openMainWindow(self, args):
        """Open the main window with any loaded files."""
        MainWindow = Graphics

        emptywins = []
        for w in self.topLevelWidgets():
            if isinstance(w, MainWindow) and w.document.isBlank():
                emptywins.append(w)
        created = 0
        if len(args) > 1:
            # load in filenames given
            for filename in args[1:]:
                if filename.endswith('.py') or filename.endswith('.pyc') or filename.endswith('.pyd'):
                    continue
                created += 1
                if not emptywins:
                    MainWindow.CreateWindow(filename)
                else:
                    emptywins[0].openFile(filename)
        if not created:
            # create blank window
            logging.debug('%s', 'creating blank window')
            MainWindow.CreateWindow()

    def startup(self):
        self.slotStartApplication()
