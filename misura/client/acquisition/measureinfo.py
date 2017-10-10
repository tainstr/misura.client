#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore
from ..procedure import thermal_cycle
from .. import conf, widgets, _
from ..live import registry
import status


class MeasureInfo(QtGui.QTabWidget):

    """Measurement and samples configuration"""
    statusView = False

    def __init__(self, remote, fixedDoc=False,  parent=None):
        self.nodes = []
        self.nodeViews = {}
        self.fromthermalCycleView = False
        self.fixedDoc = fixedDoc
        QtGui.QTabWidget.__init__(self, parent)
        self.setTabPosition(QtGui.QTabWidget.East)
        self.remote = remote
        logging.debug('MeasureInfo paths', remote.parent(
        )._Method__name, remote._Method__name, remote.measure._Method__name)
        # Configurazione della Misura
        self.server = remote.parent()
        self.measureView = conf.Interface(
            self.server, remote.measure, remote.measure.describe(), parent=None)
        # Thermal cycle - only if a kiln obj exists
        p = self.server
        if p.has_child('kiln'):
            self.thermalCycleView = thermal_cycle.ThermalCycleDesigner(
                p.kiln, remote, parent=self)
        else:
            self.thermalCycleView = QtGui.QWidget(self)
        self.results = QtGui.QWidget()

        self.nobj = widgets.ActiveObject(
            self.server, self.remote.measure, self.remote.measure.gete('nSamples'), parent=self)

        self.refreshSamples()

        self.nobj.register()
        self.connect(self.nobj, QtCore.SIGNAL('changed()'),
                     self.refreshSamples, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL("currentChanged(int)"), self.tabChanged)
        #self.connect(
        #    self, QtCore.SIGNAL("currentChanged(int)"), self.refreshSamples)

        self.tabBar().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self.show_menu)

    def set_doc(self, doc):
        self.results.set_doc(doc)

    def tabChanged(self, *foo):
        """Check if thermal cycle is saved - only if live"""
        # Do not check tc if local
        if not getattr(self.remote, 'addr'):
            return
        currentTab = self.currentWidget()
        if not currentTab == self.thermalCycleView:
            if self.fromthermalCycleView:
                self.checkCurve()
                self.fromthermalCycleView = False
        else:
            self.fromthermalCycleView = True

    def checkCurve(self):
        if not hasattr(self.thermalCycleView, 'check_if_saved'):
            return 
        remote_equals, saved_equals = self.thermalCycleView.check_if_saved()
        if not remote_equals:
            r = QtGui.QMessageBox.warning(self, _("Changes were not applied"),
                                          _(
                                              "Changes to thermal cycle were not applied! Apply now?"),
                                          QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
            if r == QtGui.QMessageBox.Ok:
                self.thermalCycleView.apply()
        # TODO: warn also about saved_equals?

    nsmp = 0

    def set_results(self, results):
        i = self.indexOf(self.results)
        if i >= 0:
            self.removeTab(i)
        i = self.statusView is not False
        i += self.indexOf(self.measureView)>0
        i += self.indexOf(self.thermalCycleView)>0
        self.results = results
        if self.fixedDoc or registry.values.get('/isRunning', False):
            self.insertTab(i, self.results, _('Navigator'))

    def refreshSamples(self, *foo):
        nsmp = self.nobj.current
        if self.nsmp == nsmp and self.nodeViews and self.nodes and self.count() > 2:
            logging.debug('NO CHANGE in samples number', self.nsmp, nsmp)
            return False
        self.nsmp = nsmp
        self.blockSignals(True)
        self.clear()
        
        if not self.fixedDoc:
            self.statusView = status.Status(
                self.server, self.remote, parent=self)
            self.addTab(self.statusView, 'Status')
            registry.system_kid_changed.connect(self.system_kid_slot)
            self.up_isRunning()
        else:
            self.statusView = False
        self.addTab(self.measureView, _('Measure'))
        if self.remote['devpath'] != 'flash':
            self.addTab(self.thermalCycleView, _('Thermal Cycle'))
        else:
            self.thermalCycleView.hide()
        self.set_results(self.results)
        self.refresh_nodes()
        self.blockSignals(False)
        return True

    def get_samples(self):
        nsmp = self.nobj.current
        self.nsmp = nsmp
        paths = []
        p0 = self.remote['fullpath']
        # Iterate one more in case its 1-based
        for i in range(self.nsmp+1):
            n = 'sample' + str(i)
            if not self.remote.has_child(n):
                continue
            sample = getattr(self.remote, n)
            paths.append(p0 + n)
        return paths

    def refresh_nodes(self, nodes=[]):
        # Remove all node tabs
        for nodevi in self.nodeViews.itervalues():
            i = self.indexOf(nodevi)
            if i < 0:
                continue
            self.removeTab(i)

        if not nodes:
            nodes = self.nodes
        if not nodes:
            nodes = self.get_samples()
        if not nodes:
            return False
        self.nodes = []
        self.menus = []
        c = self.count()+1
        for i, n in enumerate(nodes):
            if n in self.nodes:
                continue
            node = self.server.toPath(n)
            if not node:
                logging.debug('Missing node object', n)
                continue
            wg = self.nodeViews.get(n, False)
            if wg is False:
                logging.debug('MeasureInfo.refresh_nodes: creating nodeView', n)
                wg = conf.Interface(
                    self.server, node, node.describe(), parent=None)
            j = c + i
            self.insertTab(j, wg, node['devpath'].capitalize())
            self.nodeViews[n] = wg
            self.nodes.append(n)
        return True

    def show_menu(self, pos):
        tab_idx = self.tabBar().tabAt(pos)
        wg = self.widget(tab_idx)
        node = getattr(wg, 'remObj', False)
        if not node:
            return
        menu = QtGui.QMenu(self)
        self.results.navigator.build_menu_from_configuration(node, menu)
        menu.exec_(self.tabBar().mapToGlobal(pos))

    def closeEvent(self, ev):
        """Disconnect dangerous signals before closing"""
        registry.system_kid_changed.disconnect(self.system_kid_slot)
        return super(MeasureInfo, self).closeEvent(ev)

    def system_kid_slot(self, kid):
        if kid == '/isRunning':
            self.up_isRunning()

    def up_isRunning(self):
        is_running = registry.values.get('/isRunning', False)
        if hasattr(self.thermalCycleView, 'enable'):
            self.thermalCycleView.enable(not is_running)
        self.tabBar().setStyleSheet(
            "background-color:" + ('red;' if is_running else 'green;'))

        # Update isRunning widget
        self.statusView.widgets['/isRunning']._get(is_running)
        
        self.set_results(self.results)

        self.measureView.reorder()
        for wg in self.nodeViews.itervalues():
            wg.reorder()
