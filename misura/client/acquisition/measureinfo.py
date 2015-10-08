#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore
from ..procedure import thermal_cycle
from .. import conf, widgets
from ..live import registry
import status


class MeasureInfo(QtGui.QTabWidget):

    """Measurement and samples configuration"""
    statusView = False

    def __init__(self, remote, fixedDoc=False,  parent=None):
        self.fromthermalCycleView = False
        self.fixedDoc = fixedDoc
        QtGui.QTabWidget.__init__(self, parent)
        self.setTabPosition(QtGui.QTabWidget.East)
        self.remote = remote
        logging.debug('%s %s %s %s', 'MeasureInfo paths', remote.parent(
        )._Method__name, remote._Method__name, remote.measure._Method__name)
        # Configurazione della Misura
        self.server = remote.parent()
        self.measureView = conf.Interface(
            self.server, remote.measure, remote.measure.describe(), parent=self)
        # Thermal cycle - only if a kiln obj exists
        p = self.server
        if p.has_child('kiln'):
            self.thermalCycleView = thermal_cycle.ThermalCycleDesigner(
                p.kiln, remote, parent=self)
        else:
            self.thermalCycleView = QtGui.QWidget(self)
        self.results = QtGui.QWidget(self)
        # Add a tab to correct inizialization og qTabWidget
        self.addTab(self.results, 'Results')
        self.nobj = widgets.ActiveObject(
            self.server, self.remote.measure, self.remote.measure.gete('nSamples'), parent=self)
        self.nobj.register()
        self.connect(self.nobj, QtCore.SIGNAL('changed()'),
                     self.refreshSamples, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL("currentChanged(int)"), self.tabChanged)
        self.connect(
            self, QtCore.SIGNAL("currentChanged(int)"), self.refreshSamples)

    def set_doc(self, doc):
        self.results.set_doc(doc)

    def tabChanged(self):
        currentTab = self.currentWidget()
        if not currentTab == self.thermalCycleView:
            if self.fromthermalCycleView:
                self.checkCurve()
                self.fromthermalCycleView = False
        else:
            self.fromthermalCycleView = True

    def checkCurve(self):
        tbcurveremote = self.thermalCycleView.remote.get('curve')
        tbcurve = []
        for row in self.thermalCycleView.model.curve(events=True):
            tbrowcurve = []
            tbrowcurve.append(row[0])
            tbrowcurve.append(row[1])
            tbcurve.append(tbrowcurve)
        if not tbcurve == tbcurveremote:
            r = QtGui.QMessageBox.warning(self, "Changes not saved",
                                          "Changes to thermal cycle were not saved! Do you save it now?",
                                          QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
            if r == QtGui.QMessageBox.Yes:
                self.thermalCycleView.apply()

    nsmp = 0

    def refreshSamples(self, *foo):
        #		nsmp=self.remote.measure['nSamples']
        nsmp = self.nobj.current
        if self.nsmp == nsmp:
            logging.debug(
                '%s %s %s', 'NO CHANGE in samples number', self.nsmp, nsmp)
            return False
        self.nsmp = nsmp
        self.clear()
        if not self.fixedDoc:
            self.statusView = status.Status(
                self.server, self.remote, parent=self)
            self.addTab(self.statusView, 'Status')
            registry.system_kid_changed.connect(self.system_kid_slot)
            self.up_isRunning()
        else:
            self.statusView = False
        self.addTab(self.measureView, 'Measure')
        self.addTab(self.thermalCycleView, 'Thermal Cycle')
        logging.debug(
            '%s %s', 'REFRESH SAMPLES', self.remote.measure['nSamples'])
        for i in range(self.nsmp):
            sample = getattr(self.remote, 'sample' + str(i), False)
            if not sample:
                logging.debug('%s %s', 'Missing sample object nr.', i)
                continue
            self.addTab(conf.Interface(
                self.remote.parent(), sample, sample.describe(), self), 'Sample' + str(i))
        self.addTab(self.results, 'Results')
        return True

    def closeEvent(self, ev):
        """Disconnect dangerous signals before closing"""
        registry.system_kid_changed.disconnect(self.system_kid_slot)
        return super(MeasureInfo, self).closeEvent(ev)

    def system_kid_slot(self, kid):
        if kid == '/isRunning':
            self.up_isRunning()

    def up_isRunning(self):
        val = registry.values.get('/isRunning', False)
        if val:
            self.tabBar().setStyleSheet("background-color:red;")
        else:
            self.tabBar().setStyleSheet("background-color:green;")
        # Update isRunning widget
        self.statusView.widgets['/isRunning']._get(val)
