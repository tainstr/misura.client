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
from ..database import getDatabaseWidget, getRemoteDatabaseWidget, ProgressBar
import veuszplot
from ..confwidget import RecentMenu, ClientConf


setting.transient_settings['unsafe_mode'] = True

# Caricamento icone


def loadIcons():
    """Icons loading. Must be called after qapplication init."""
    # d=list(os.path.split(veusz.utils.utilfuncs.resourceDirectory))[:-1]+['misura','client','art']
    # artdir=os.path.join(*tuple(d))

    for key in ['m4.connect', 'm4.db', 'm4.open', 'm4.sintering', 'm4.softening', 'm4.sphere', 'm4.halfSphere', 'm4.melting']:
        n = key.split('.')[1] + '.svg'
        n = os.path.join(params.pathArt, n)
        logging.debug('%s', n)
        if not os.path.exists(n):
            continue
        veusz.utils.action._iconcache[key] = QtGui.QIcon(n)


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

    # lookup filename
    filename = unicode(filename)
    realfilename = self.findFileOnImportPath(filename)
    logging.debug('%s %s %s', 'open_file:', filename, realfilename)
    p = filedata.ImportParamsMisura(filename=realfilename, **options)
    op = filedata.OperationMisuraImport(p)

    self.document.applyOperation(op)
    confdb.mem_file(realfilename, op.measurename)
    dsnames = op.outdatasets
    logging.debug('%s %s', "Imported datasets %s" % (' '.join(dsnames), ))
    return dsnames

# Add the ImportMisura command to the CommandInterface class
imp = 'ImportMisura'
safe = list(document.CommandInterface.safe_commands)
safe.append(imp)
document.CommandInterface.safe_commands = safe
document.CommandInterface.ImportMisura = misura_import


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
        for widgettype in ('datapoint', 'intercept', 'synaxis', 'imagereference'):
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
        self.cc = ClientConf().show()

    def update_page(self, *foo):
        """Update the navigator view in order to show colours and styles 
        effectively present in the current page"""
        n = self.mw.plot.getPageNumber()
        page = self.mw.document.basewidget.getPage(n)
        if page is None:
            logging.debug('%s %s', 'NO PAGE FOUND', n)
            return
        logging.debug('%s %s', 'update_page', page.path)
        self.openedFiles.model().set_page(page.path)
        logging.debug('%s', 'done model.set_page')
        for p in self.mw.document.basewidget.children:
            if not p.typename == 'page':
                continue
            self.update_title(p)
        self.connect(
            self.mw.plot, QtCore.SIGNAL("sigUpdatePage"), self.update_page)

    def update_title(self, pg):
        """Update title label if present in page `pg`"""
#       print 'Update title',pg.path
        if pg.getChild('title') is None:
            return
        avplot = self.openedFiles.model().plots['plot']
        datasets = []
        for p in avplot:
            if p.startswith(pg.path):
                datasets += avplot[p]
        if len(datasets) == 0:
            return
        smpl = []
        tit = []
        for ds in datasets:
            smp = getattr(ds, 'm_smp', False)
            if not smp:
                continue
            if smp in smpl:
                continue
            if smp.ref:
                continue
            smpl.append(smp)
            tit.append(smp.conf['name'])

        twg = pg.getChild('title')
        tit = 'Title' if len(tit) == 0 else ' + '.join(tit)
        tit = tit.replace('_', '\\_')
        if twg.settings.label != tit:
            twg.settings.label = tit
            self.mw.plot.actionForceUpdate()

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
        self.openedFiles.refresh()

    def open_file(self, filename,  **options):
        """Import misura data from HDF file"""
        options['rule_inc'] = confdb['rule_inc']
        options['rule_exc'] = confdb['rule_inc']
        options['rule_load'] = confdb['rule_load'] + '\n' + confdb['rule_plot']
        options['rule_unit'] = confdb['rule_unit']
        # lookup filename
        filename = unicode(filename)
        dsnames = self.mw.cmd.ImportMisura(filename, **options)
        self.openedFiles.refresh()
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

    def open_database(self, path):
        db = misura3.m3db.TestDialog(path=path)
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
        loadIcons()
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
        # self.m3=Misura3Interface(self)

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

        if len(args) > 1:
            # load in filenames given
            for filename in args[1:]:
                if filename.endswith('.py') or filename.endswith('.pyc') or filename.endswith('.pyd'):
                    continue
                if not emptywins:
                    MainWindow.CreateWindow(filename)
                else:
                    emptywins[0].openFile(filename)
        else:
            # create blank window
            logging.debug('%s', 'creating blank window')
            MainWindow.CreateWindow()

    def startup(self):
        self.slotStartApplication()
