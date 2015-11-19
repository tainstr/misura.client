#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
from misura.canon.logger import Log as logging
from .. import _
from .. import widgets
from PyQt4 import QtGui, QtCore
import row
from ..network.mproxy import MisuraProxy
from .. import conf

from plot import ThermalCyclePlot
from table import ThermalCurveTable
import veusz.utils
from misura.client import iutils


class ThermalCycleDesigner(QtGui.QSplitter):

    """The configuration interface widget. It builds interactive controls to deal with a misura configuration object (options, settings, peripherals configurations, etc)."""

    def __init__(self, remote, active_instrument, parent=None, force_live=False):
        iutils.loadIcons()
        #       QtGui.QWidget.__init__(self, parent)
        QtGui.QSplitter.__init__(self, parent)
        self.setOrientation(QtCore.Qt.Vertical)
        self.remote = remote
        self.main_layout = self
#       self.main_layout=QtGui.QVBoxLayout()
#       self.setLayout(self.main_layout)
        menuBar = QtGui.QMenuBar(self)
        menuBar.setNativeMenuBar(False)
        self.main_layout.addWidget(menuBar)

        is_live = isinstance(remote, MisuraProxy) or force_live

        self.table = ThermalCurveTable(remote, self, is_live=is_live)
        self.model = self.table.model()

        if is_live:
            self.fileMenu = menuBar.addMenu(_('File'))
            self.fileMenu.addAction(_('Import from CSV'), self.loadCSV)
            self.fileMenu.addAction(_('Export to CSV'), self.exportCSV)
            self.fileMenu.addAction(_('Clear table'), self.clearTable)
            self.editMenu = menuBar.addMenu(_('Edit'))
            self.editMenu.addAction(_('Insert point'), self.table.newRow)
            self.editMenu.addAction(
                _('Insert checkpoint'), self.table.newCheckpoint)
            self.editMenu.addAction(_('Insert natural cooling'), self.table.newCool)
            self.editMenu.addAction(_('Insert movement'), self.table.newMove)
            self.editMenu.addAction(
                _('Insert control transition'), self.table.newThermocoupleControlTransition)
            a = self.editMenu.addAction(
                'Insert parametric heating', self.table.newParam)
            a.setEnabled(False)
            self.editMenu.addAction('Remove current row', self.table.delRow)
            self.templatesMenu = menuBar.addMenu(_('Templates'))

            self.templatesMenu.addAction(veusz.utils.action.getIcon('m4.single-ramp'), _('Single Ramp'), self.singl_ramp_template)
            self.addButtons()

        self.plot = ThermalCyclePlot()
        self.connect(self.model, QtCore.SIGNAL(
            "dataChanged(QModelIndex,QModelIndex)"), self.replot)
        self.addTable()

        self.main_layout.addWidget(self.table)

        thermal_cycle_options = {}
        for opt in ('onKilnStopped', 'kilnBeforeStart','kilnAfterEnd','duration',
                    'coolingBelowTemp', 'coolingAfterTime'):
            if not active_instrument.measure.has_key(opt):
                logging.debug('Measure has no option %s', opt)
                continue
            thermal_cycle_options[opt] = active_instrument.measure.gete(opt)
            print 'OPT', thermal_cycle_options[opt]
        if thermal_cycle_options:
            self.thermal_cycle_optionsWidget = conf.Interface(
            active_instrument.root, active_instrument.measure, thermal_cycle_options, parent=self)
            self.main_layout.addWidget(self.thermal_cycle_optionsWidget)
        self.main_layout.addWidget(self.plot)

    def singl_ramp_template(self):
        pass

    def enable(self, enabled):
        self.table.enable(enabled)
        self.buttonBar.setEnabled(enabled)
        self.fileMenu.setEnabled(enabled)
        self.editMenu.setEnabled(enabled)

    def replot(self, *args):
        crv = self.model.curve(events=False)
        logging.debug('%s %s', 'replotting', crv)
        self.plot.setCurve(crv)

    def addButtons(self):
        # General buttons:
        self.buttonBar = QtGui.QWidget()
        self.buttons = QtGui.QHBoxLayout()
        self.buttonBar.setLayout(self.buttons)

        self.bRead = QtGui.QPushButton("Read")
        self.connect(self.bRead, QtCore.SIGNAL('clicked(bool)'), self.refresh)
        self.buttons.addWidget(self.bRead)

        self.bApp = QtGui.QPushButton("Apply")
        self.connect(self.bApp, QtCore.SIGNAL('clicked(bool)'), self.apply)
        self.buttons.addWidget(self.bApp)
        self.tcc = widgets.ThermalCycleChooser(self.remote, parent=self, table=self.table)
        self.tcc.label_widget.hide()
        self.buttons.addWidget(self.tcc)
        self.connect(self.tcc.combo, QtCore.SIGNAL(
            'currentIndexChanged(int)'), self.refresh)
        self.connect(self.tcc, QtCore.SIGNAL('changed()'), self.refresh)
        # Disconnect save button from default call
        self.tcc.disconnect(
            self.tcc.bSave, QtCore.SIGNAL('clicked(bool)'), self.tcc.save_current)
        # Connect to apply_and_save
        self.connect(self.tcc.bSave, QtCore.SIGNAL(
            'clicked(bool)'), self.apply_and_save)
        self.main_layout.addWidget(self.buttonBar)

    def addTable(self, crv=None):
        if crv == None:
            crv = self.remote.get('curve')
            logging.debug('%s %s', 'got remote curve', crv)
        if len(crv) == 0:
            crv = [[0, 0]]
#           self.plot.hide()
        if not self.plot.isVisible():
            self.plot.show()
        pb = QtGui.QProgressBar(self)
        pb.setMinimum(0)
        pb.setMaximum(len(crv))
        self.main_layout.addWidget(pb)
        self.table.setCurve(crv, progressBar=pb)
        self.replot()
        pb.hide()
        pb.close()
        del pb

    def clearTable(self):
        self.addTable([])

    def refresh(self, *args):
        logging.debug('%s', 'ThermalCycleDesigner.refresh')
        self.addTable()

    def apply(self):
        crv = self.table.curve()
        self.remote.set('curve', crv)
        self.refresh()

    def apply_and_save(self):
        self.apply()
        self.tcc.save_current()

    def loadCSV(self):
        fname = QtGui.QFileDialog.getOpenFileName(
            self, 'Choose a *.csv file containing a time-temperature curve', '', "CSV Files (*.csv)")
        logging.debug('%s', fname)
        f = open(fname, 'r')
        crv = []
        for row in f:
            if row[0] == '#':
                continue
            row = row.replace(',', '.')
            row = row.split(';')
            t = float(row[0])
            T = row[1]
            if not T.startswith('>'):
                T = float(T)
            crv.append([t, T])
        self.addTable(crv)

    def exportCSV(self):
        fname = QtGui.QFileDialog.getSaveFileName(
            self, 'Choose destination file name', '', "CSV Files (*.csv)")
        f = open(fname, 'w')
        f.write('#time ; temp ; checkpoint\n')
        for row in self.model.curve(events=True):
            tpl = "{:.3f} ; {:.3f} \n"
            if isinstance(row[1], basestring):
                tpl = "{:.3f} ; {} \n"
            f.write(tpl.format(*row))
