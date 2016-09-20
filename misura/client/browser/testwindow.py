#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore
from .. import _
from .. import filedata
from .. import fileui
from .. import acquisition
from ..live import registry
from misura.canon.csutil import profile
from ..graphics import Breadcrumb, Storyboard

class TestWindow(acquisition.MainWindow):

    """View of a single test file"""

    def __init__(self, doc, parent=None):
        acquisition.MainWindow.__init__(self, doc=doc, parent=parent)
        self.play = filedata.FilePlayer(self)
        self.play.set_doc(doc)
        self.play.sleep = 0.1
        self.load_version(-1)

        self.controls.server = self.play
# 		self.controls.remote=self.play
        for pic, win in self.cameras.itervalues():
            pic.setSampleProcessor(self.play)
# 			d=self.doc.decoders['/dat/'+pic.role]
# 			pic.setFrameProcessor(d)

        self.graphWin.showMaximized()
# 		self.summaryPlot.default_plot()
        self.removeToolBar(self.controls)
        self.connect(self.play, QtCore.SIGNAL('set_idx(int)'), self.set_idx)
        self.connect(self.imageSlider, QtCore.SIGNAL(
            'set_idx(int)'), self.play.set_idx)

        registry.taskswg.removeStorageAndRemoteTabs()

    vtoolbar = False
    breadcrumb = False
# 	@profile
    def load_version(self, v=-1):
        logging.debug('%s %s', "SETTING VERSION", v)
        if not self.fixedDoc.proxy.isopen():
            self.fixedDoc.proxy.reopen()
        self.fixedDoc.proxy.set_version(v)
        if self.fixedDoc.proxy.conf is False:
            self.fixedDoc.proxy.load_conf()
        self.setServer(self.fixedDoc.proxy.conf)
        self.name = self.fixedDoc.proxy.get_node_attr('/conf', 'instrument')
        self.imageSlider.slider.choice()
        self.imageSlider.strip.set_idx()
        self.title = self.remote.measure['name']
        self.setWindowTitle('Test: ' + self.remote.measure['name'])

        # Menu Bar mod
        self.actStandard = self.myMenuBar.measure.addAction(
            _('Re-evaluate standards'), self.re_standard)

        self.menuVersions = fileui.VersionMenu(self.fixedDoc.proxy)
        self.myMenuBar.measure.addMenu(self.menuVersions)
        self.menuPlot = fileui.SavePlotMenu(self.fixedDoc)
        self.myMenuBar.measure.addMenu(self.menuPlot)
        self.menuVersions.versionChanged.connect(self.load_version)
        
        if self.vtoolbar:
            self.vtoobar.hide()
        self.vtoolbar = self.summaryPlot.plot.createToolbar(self)
        self.vtoolbar.addAction(' Undo ',self.doc.undoOperation)
        self.vtoolbar.show()
        self.graphWin.show()
        if self.breadcrumb:
            self.breadcrumb.hide()
        self.breadbar = QtGui.QToolBar(_('Breadcrumb'), self)
        self.breadcrumb = Breadcrumb(self.breadbar)
        self.breadcrumb.set_plot(self.summaryPlot)
        self.breadbar.addWidget(self.breadcrumb)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.breadbar)
        self.breadbar.show()
        
        self.plotboardDock = QtGui.QDockWidget(self.centralWidget())
        self.plotboardDock.setWindowTitle('Plots Board')
        self.plotboard = Storyboard(self)
        self.plotboard.set_plot(self.summaryPlot)
        self.plotboardDock.setWidget(self.plotboard)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.plotboardDock)
        # TODO: cleanup this! Should pass through some sort of plugin or config mechanism...
        if self.name not in ['flash']:
            self.plotboardDock.hide()
            self.breadbar.hide()
        else:
            self.navigator.status.add(filedata.dstats.outline)
        

    def closeEvent(self, ev):
        should_not_close_application = True
        ret = QtGui.QMainWindow.closeEvent(self,ev)
        return ret

    def close(self):
        self.play.close()
        self.fixedDoc.proxy.close()
        acquisition.MainWindow.close(self)

    def set_idx(self, idx):
        logging.debug(
            '%s %s %s', 'TestWindow.set_idx', self.play.isRunning(), idx)
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
            logging.debug(
                '%s', 'Error: restandard is only possible on local files')
            return
        # Overwrite
        r = self.fixedDoc.proxy.run_scripts(self.remote)
        if r:
            # 			# Update every ActiveWidget connected to the registry
            registry.force_redraw()
            self.summaryPlot.resize(self.summaryPlot.size())
