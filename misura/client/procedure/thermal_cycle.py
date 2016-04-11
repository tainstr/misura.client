#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
from traceback import format_exc

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
from misura.canon import option


def ramp_to_thermal_cycle_curve(end_temperature, heating_rate):
    time_elapsed_in_seconds = end_temperature / float(heating_rate) * 60.
    return [[0.0, 0], [time_elapsed_in_seconds, end_temperature]]


def steps_template_to_thermal_cycle_curve(values):
    heating_rate = values['heatingRate']
    number_of_steps = values['numberOfSteps']
    step_duration = values['stasisDuration']
    step_delta_T = values['stepsDeltaT']
    first_step_temperature = values['firstStepTemperature']
    step_ramp_duration = float(step_delta_T) / heating_rate * 60

    curve = ramp_to_thermal_cycle_curve(first_step_temperature, heating_rate)
    curve.append([last_point_time(curve) + step_duration, first_step_temperature])

    for current_step in range(number_of_steps-1):
        ramp_end_time = last_point_time(curve) + step_ramp_duration
        ramp_end_remperature = last_point_temperature(curve) + step_delta_T

        curve.append([ramp_end_time, ramp_end_remperature])
        curve.append([ramp_end_time + step_duration, ramp_end_remperature])

    return curve

def last_point_time(curve):
    return curve[-1][0]

def last_point_temperature(curve):
    return curve[-1][1]

def get_progress_time_for(current_segment_progress, kiln):
    all_segments = kiln['segments']
    current_segment_position = kiln['segmentPos'] - 1
    current_segment = all_segments[current_segment_position]
    time = 0

    if current_segment_position > 0:
        time += all_segments[current_segment_position-1][-1][0]

    result = (time + (current_segment[-1][0] - time) * current_segment_progress / 100.) / 60.
    return result

class ThermalCycleDesigner(QtGui.QSplitter):

    """The configuration interface widget. It builds interactive controls to deal with a misura configuration object (options, settings, peripherals configurations, etc)."""

    def __init__(self, remote, active_instrument, parent=None, force_live=False):
        iutils.loadIcons()
        QtGui.QSplitter.__init__(self, parent)
        self.parent = parent
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
        self.table.doubleClicked.connect(self.set_mode_of_cell)
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
            self.editMenu.addAction(
                _('Insert natural cooling'), self.table.newCool)
            self.editMenu.addAction(_('Insert movement'), self.table.newMove)
            self.editMenu.addAction(
                _('Insert control transition'), self.table.newThermocoupleControlTransition)
            a = self.editMenu.addAction(
                'Insert parametric heating', self.table.newParam)
            a.setEnabled(False)
            self.editMenu.addAction('Remove current row', self.table.delRow)
            self.templatesMenu = menuBar.addMenu(_('Templates'))

            self.templatesMenu.addAction(veusz.utils.action.getIcon(
                'm4.single-ramp'), _('Single Ramp'), self.single_ramp_template)
            self.templatesMenu.addAction(
                veusz.utils.action.getIcon('m4.steps'), _('Steps'), self.steps_template)
            self.addButtons()

            self.progress = widgets.ActiveObject(self.remote.parent,
                                                 self.remote,
                                                 self.remote.gete('segmentProgress'),
                                                 parent=self)
            self.progress.register()

            self.connect(self.progress,
                         QtCore.SIGNAL('changed'),
                         self.progress_changed)

            self.connect(self.table,
                         QtCore.SIGNAL('pressed(QModelIndex)'),
                         self.synchronize_progress_bar_to_table)


        self.plot = ThermalCyclePlot()
        self.connect(self.model, QtCore.SIGNAL(
            "dataChanged(QModelIndex,QModelIndex)"), self.replot)
        self.addTable()

        self.main_layout.addWidget(self.table)

        thermal_cycle_options = {}
        for opt in (
            'onKilnStopped', 'kilnBeforeStart', 'kilnAfterEnd', 'duration',
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

    def progress_changed(self, current_segment_progress):
        self.plot.set_progress(get_progress_time_for(current_segment_progress,
                                                     self.remote))

    def synchronize_progress_bar_to_table(self, *ignored):
        index = self.table.currentIndex()
        progress_time = index.sibling(index.row(), 0).data()
        progress_time = progress_time or 0
        self.plot.set_progress(progress_time)

    def set_mode_of_cell(self, index_model):
        if index_model.column() != row.colTEMP:
            self.model.update_mode_of_row_with_mode_of_column(
                index_model.row(), index_model.column())

    def single_ramp_template(self):
        ramp_options = {}
        option.ao(
            ramp_options, 'temperature', 'Float', name=_("Ramp end Temperature"),
                  unit='celsius', current=1000, min=0, max=2000, step=0.1)
        option.ao(ramp_options, 'heatingRate', 'Float', name=_("Heating Rate"),
                  unit='celsius/minute', current=20, min=0.1, max=80, step=0.1)
        temperature_configuration_proxy = option.ConfigurationProxy(
            {'self': ramp_options})
        temperature_dialog = conf.InterfaceDialog(
            temperature_configuration_proxy, temperature_configuration_proxy, ramp_options, parent=self.parent)
        temperature_dialog.setWindowTitle(_('Single ramp template'))
        if temperature_dialog.exec_():
            new_curve = ramp_to_thermal_cycle_curve(temperature_configuration_proxy[
                                                    'temperature'], temperature_configuration_proxy['heatingRate'])
            self.model.setCurve(new_curve)
            self.replot()
            self.apply()

    def steps_template(self):
        steps_options = {}
        option.ao(
            steps_options, 'heatingRate', 'Float', name=_("Heating Rate"),
                  unit='celsius/minute', current=80, min=0.1, max=80, step=0.1)
        option.ao(
            steps_options, 'firstStepTemperature', 'Float', name=_("First step Temperature"),
                  unit='celsius', current=1000, min=0, max=1800, step=0.1)
        option.ao(
            steps_options, 'stasisDuration', 'Float', name=_("Stasis Duration"),
                  unit='seconds', current=600, step=1)
        option.ao(steps_options, 'numberOfSteps', 'Integer',
                  name=_("Number of Steps"), current=10, step=1)
        option.ao(
            steps_options, 'stepsDeltaT', 'Float', name=_("Steps delta T"),
                  unit='celsius', current=20, min=0, max=100, step=0.1)

        configuration_proxy = option.ConfigurationProxy(
            {'self': steps_options})
        temperature_dialog = conf.InterfaceDialog(
            configuration_proxy, configuration_proxy, steps_options, parent=self.parent)
        temperature_dialog.setWindowTitle(_('Single ramp template'))
        if temperature_dialog.exec_():
            new_curve = steps_template_to_thermal_cycle_curve(configuration_proxy)
            self.model.setCurve(new_curve)
            self.replot()
            self.apply()

    def enable(self, enabled):
        self.table.enable(enabled)
        try:
            self.buttonBar.setEnabled(enabled)
            self.fileMenu.setEnabled(enabled)
            self.editMenu.setEnabled(enabled)
        except:
            logging.debug(format_exc())

    def replot(self, *args):
        crv = self.model.curve(events=False)
        logging.debug('%s %s', 'replotting', crv)
        self.plot.setCurve(crv)
        self.synchronize_progress_bar_to_table()

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
        self.tcc = widgets.ThermalCycleChooser(
            self.remote, parent=self, table=self.table)
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
