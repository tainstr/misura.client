#!/usr/bin/python
# -*- coding: utf-8 -*-
from functools import partial
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from PyQt4 import QtGui, QtCore

import veusz.utils

from .. import _
from .. import filedata
from .. import fileui
from .. import acquisition
from ..live import registry
from misura.canon.csutil import profile
from ..graphics import Breadcrumb, Storyboard
from ..navigator import NavigatorToolbar
from misura.client.iutils import calc_plot_hierarchy, most_involved_node

class TestWindow(acquisition.MainWindow):

    """View of a single test file"""
    loaded_version = QtCore.pyqtSignal(str)
    
    def __init__(self, doc, parent=None):
        acquisition.MainWindow.__init__(self, doc=doc, parent=parent)
        self.play = filedata.FilePlayer(self)

        self.load_version(-1)

        registry.taskswg.removeStorageAndRemoteTabs()

    vtoolbar = False
    breadcrumb = False
    breadbar = False
    plotboard=False
    menuVersions = False
    navtoolbar = False
    initial_veusz_doc_changeset = -1
    
    def load_version(self, v=-1):
        self.fixedDoc.paused = True
        logging.debug("SETTING VERSION", v)
        self.plot_page = False
        if not self.fixedDoc.proxy.isopen():
            self.fixedDoc.proxy.reopen()
            
        self.fixedDoc.proxy.set_version(v)
        
        if self.fixedDoc.proxy.conf is False:
            logging.debug('load_conf')
            self.fixedDoc.proxy.load_conf()
        self.fixedDoc.proxy.conf.filename = self.fixedDoc.proxy.path
        self.fixedDoc.proxy.conf.doc = self.fixedDoc
        
        self.setServer(self.fixedDoc.proxy.conf)
        
        self.fixedDoc.proxy.conf._navigator = self.navigator
        self.name = self.fixedDoc.proxy.get_node_attr('/conf', 'instrument')
        self.imageSlider.slider.choice()
        self.imageSlider.strip.set_idx()
        self.title = self.remote.measure['name']
        self.setWindowTitle('Test: ' + self.remote.measure['name'])

        # Menu Bar mod

        
        self.create_version_plot_menus()
        
        #self.measure_toolbar = QtGui.QToolBar(self)
        #self.addToolBar(QtCore.Qt.TopToolBarArea, self.measure_toolbar)
        
        
        if self.vtoolbar:
            self.vtoolbar.hide()
        self.vtoolbar = self.summaryPlot.plot.createToolbar(self)
        veusz.utils.addToolbarActions(self.vtoolbar, 
                                      self.summaryPlot.treeedit.vzactions, 
                                      ('add.key', 'add.label', 'add.shapemenu'))
        self.vtoolbar.show()
        
        self.navtoolbar = NavigatorToolbar(self.navigator, self)
        self.navtoolbar.show()
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.navtoolbar)
        self.navtoolbar.versionSaved.connect(self.reset_changeset)
        
        self.graphWin.show()
        
        
        self.add_breadcrumb()
        self.add_plotboard()
        

        # TODO: cleanup this! Should pass through some sort of plugin or config
        # mechanism...
        if self.name not in ['flash']:
            self.plotboardDock.hide()
            self.breadbar.hide()
        else:
            self.navigator.status.add(filedata.dstats.outline)
            try:
                self.summaryPlot.cmd.Remove('/time')
            except:
                pass

        
        self.doc.model.sigPageChanged.connect(self.slot_page_changed)
        
        self.add_playback()

        self.graphWin.showMaximized()
        self.removeToolBar(self.controls)
        self.connect(self.play, QtCore.SIGNAL('set_idx(int)'), self.set_idx)
        self.connect(self.imageSlider, QtCore.SIGNAL('set_idx(int)'), 
                     self.play.set_idx)
        
        
        
        self.fixedDoc.paused = False 
        
        self.reset_changeset()
        self.loaded_version.emit(self.fixedDoc.proxy.get_version())
        
    def get_tooltip(self):
        """This is shown in tabbar"""
        m = self.remote.measure
        tt = [self.fixedDoc.proxy.get_path(), m['name']]
        cm = m['comment']
        if cm:
            tt.append(cm)
        for smp in self.remote.samples:
            tt.append(smp['name'])
        tt.append(m['date'])
        return '\n'.join(tt)
        
    def reset_changeset(self, *foo):
        self.initial_veusz_doc_changeset = self.doc.changeset-self.doc.changeset_ignore
        self.initial_server_changeset = self.server.recursive_changeset()
        logging.debug('Reset changeset', self.initial_veusz_doc_changeset,
                      self.initial_server_changeset)
        
    def add_playback(self):
        """FIXME: DISABLED"""
        self.play = filedata.FilePlayer(self)
        self.play.set_doc(self.fixedDoc)
        self.play.sleep = 0.1
        self.controls.remote=self.play
        for pic, win in self.cameras.itervalues():
            pic.setSampleProcessor(self.play)
#             d=self.doc.decoders['/dat/'+pic.role]
#             pic.setFrameProcessor(d)       
        
        
    def add_breadcrumb(self):
        if self.breadbar:
            self.removeToolBar(self.breadbar)
            self.breadcrumb.hide()
            self.breadcrumb.deleteLater()
        self.breadbar = QtGui.QToolBar(_('Breadcrumb'), self)
        self.breadcrumb = Breadcrumb(self.breadbar)
        self.breadcrumb.set_plot(self.summaryPlot)
        self.breadbar.addWidget(self.breadcrumb)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.breadbar)
        self.breadbar.show() 
        
    def add_plotboard(self):
        if self.plotboard:
            self.plotboard.blockSignals(True)
            self.rem('plotboardDock', 'plotboard')            
        self.plotboardDock = QtGui.QDockWidget(self.centralWidget())
        self.plotboardDock.setWindowTitle('Plots Board')
        self.plotboard = Storyboard(self)
        self.plotboard.set_plot(self.summaryPlot)
        self.plotboardDock.setWidget(self.plotboard)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.plotboardDock) 
        self.myMenuBar.add_view_plotboard()       
        
    def create_version_plot_menus(self):
        self.actStandard = self.myMenuBar.measure.addAction(
            _('Re-calculate metadata'), self.re_standard)
        if not self.menuVersions:
            self.menuVersions = fileui.VersionMenu(self.fixedDoc, self.fixedDoc.proxy)
            self.menuVersions.versionChanged.connect(partial(self.slot_version_changed))
            self.menuVersions.versionSaved.connect(self.reset_changeset)
        self.myMenuBar.measure.addMenu(self.menuVersions)
        
    def slot_version_changed(self):
        """Proxy version changed. Need to refresh all ConfigurationInterface objects"""
        self.server = self.fixedDoc.proxy.conf
        self.remote = self.server.instrument_obj
        self.add_measure()
        self.add_sumtab()
        self.add_table()
        self.add_menubar()

        self.create_version_plot_menus()
        self.navigator.set_doc(self.doc)
        self.measureTab.results.set_doc(self.doc)
        
        

    def slot_page_changed(self):
        p = self.summaryPlot.plot.getPageNumber()
        page = self.doc.basewidget.children[p]
        if page == self.plot_page:
            return False
        self.plot_page = page

        hierarchy, level, page_idx = calc_plot_hierarchy(self.fixedDoc, page)
        if level < 0:
            return False
        plots = hierarchy[level][page_idx][1]
        crumbs, most_commons = most_involved_node(plots, self.doc)
        get_path = lambda crumbs: '/' + \
            '/'.join([c.split(':')[-1] for c in crumbs])
        paths = []
        if len(crumbs) > 0:
            if len(crumbs) > 1:
                paths.append(get_path(crumbs))
            if len(crumbs) > len(most_commons):
                self.measureTab.refresh_nodes(paths)
                return True
            
            if len(crumbs) == len(most_commons):
                crumbs.pop(-1)

            p = get_path(crumbs)
            for c in sorted(most_commons[-1]):
                paths.append(p + '/' + c)
        self.measureTab.refresh_nodes(paths)
        return True

    def closeEvent(self, ev):
        ret = self.close()
        if ret:
            ret = QtGui.QMainWindow.closeEvent(self, ev)
        return ret
    
    def check_save(self):
        effective_changeset = self.doc.changeset-self.doc.changeset_ignore
        conf_changeset = self.server.recursive_changeset()
        logging.debug('Checking changesets', effective_changeset, self.doc.changeset,  
                      self.initial_veusz_doc_changeset, conf_changeset, self.initial_server_changeset)
        if effective_changeset > self.initial_veusz_doc_changeset or conf_changeset>self.initial_server_changeset:
            ver = self.doc.proxy.get_version()
            logging.debug('got version', repr(ver))
            if not ver:
                ver = _('a new version')
            else:
                ver = _('on version: ')+ver             
            r = QtGui.QMessageBox.question(self, _('Save changes'), 
                                       _('Some changes were detected. \nWould you like to save ')+ver+' ?',
                                       QtGui.QMessageBox.Ok|QtGui.QMessageBox.Discard|QtGui.QMessageBox.Abort)
            if r==QtGui.QMessageBox.Abort:
                logging.debug('Aborting close action.')
                return False
            elif r==QtGui.QMessageBox.Ok:
                logging.debug('Saving a version on close', ver)
                v = fileui.VersionMenu(self.doc, self.doc.proxy)
                v.save_version()
        return True
    
    def close(self):                
        self.play.close()
        self.fixedDoc.proxy.close()
        return acquisition.MainWindow.close(self)

    def set_idx(self, idx):
        logging.debug('TestWindow.set_idx', self.play.isRunning(), idx)
        if not self.play.isRunning():
            self.play.set_idx(idx)
        else:
            if idx == self.imageSlider.value():
                return
            self.imageSlider.set_idx(idx)

    def re_standard(self):
        """Re-evaluate the meta-data generating scripts (standards)."""
        fp = self.fixedDoc.proxy
        if fp.__class__.__name__ != 'SharedFile':
            logging.debug('Error: restandard is only possible on local files')
            return
        # Overwrite
        r = self.fixedDoc.proxy.run_scripts(self.remote)
        r = self.fixedDoc.proxy.conf.update_aggregates(recursive=-1)
        if r:
            # 			# Update every ActiveWidget connected to the registry
            registry.force_redraw()
            self.summaryPlot.resize(self.summaryPlot.size())
