#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
from misura.canon.logger import Log as logging
from .. import _
from .. import widgets
from misura.canon import option
from misura.canon.csutil import next_point
from .. import conf
from .. import units
from PyQt4 import QtGui, QtCore
import row
from ..network.mproxy import MisuraProxy

from plot import ThermalCyclePlot
from time_spinbox import TimeSpinBox
from model import ThermalCurveModel, clean_curve
from delegate import ThermalPointDelegate


class ThermalCurveTable(QtGui.QTableView):

    """Table view of a thermal cycle."""

    def __init__(self, remote, parent=None, is_live=True):
        QtGui.QTableView.__init__(self, parent)
        self.curveModel = ThermalCurveModel(is_live=is_live)
        self.setModel(self.curveModel)
        self.setItemDelegate(ThermalPointDelegate(remote, self))
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        if is_live:
            self.menu = QtGui.QMenu(self)
            m = self.menu
            m.addAction(_('Insert point'), self.newRow)
            m.addAction(_('Insert checkpoint'), self.newCheckpoint)
            if self.motor_is_available(remote):
                m.addAction(_('Insert movement'), self.newMove)
            m.addAction(_('Insert control transition'), self.newThermocoupleControlTransition)
    #       a=m.addAction(_('Insert parametric heating'), self.newParam)
    #       a.setEnabled(False)
            m.addAction(_('Remove current row'), self.delRow)
            m.addSeparator()
            # self.curveModel.mode_ramp(0)

    def motor_is_available(self, kiln):
        return not (kiln["motor"][0] == "None")

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))

    def setCurve(self, crv, progressBar=False):
        self.model().setCurve(crv, progressBar)

    def curve(self):
        return self.model().curve()

    ### ADD/DEL ####
    def newRow(self):
        crow = self.selection.currentIndex().row()

        row_to_copy = row.previous_not_event_row_index(
            crow, self.model().dat)
        values = self.model().dat[row_to_copy][:]

        self.model().insertRows(crow + 1, values=values)

    def insert_event(self, event):
        """Insert new `event` at current row"""
        crow = self.selection.currentIndex().row()
        # Find latest valid time from crow
        t = 0
        idx, ent = next_point(self.model().dat, crow, -1)
        if ent is not False:
            t = ent[0]
        self.model().insertRows(crow + 1, values=[t, event, 0, 0])
        self.setSpan(crow + 1, row.colTEMP, 1, 3)

    def newMove(self):
        items = ['>move,close', '>move,open']
        labels = [_('Close furnace'), _('Open furnace')]
        item, ok = QtGui.QInputDialog.getItem(
            self, _('Select furnace movement event'), _('Event type:'), labels, 0, False)
        if ok:
            val = labels.index(item)
            val = items[val]
            self.insert_event(val)
        return ok

    def newCheckpoint(self):
        desc = {}
        option.ao(desc, 'deltaST', 'Float', name=_("Temperature-Setpoint tolerance"),
                  unit='celsius', current=3, min=0, max=100, step=0.1)
        option.ao(desc, 'timeout', 'Float', name=_("Timeout"),
                  unit='minute', current=120, min=0, max=1e3, step=0.1)
        cp = option.ConfigurationProxy({'self': desc})
        chk = conf.InterfaceDialog(cp, cp, desc, parent=self)
        chk.setWindowTitle(_("Checkpoint configuration"))
        ok = chk.exec_()
        if ok:
            timeout = units.Converter.convert('minute', 'second', cp['timeout'])
            event = '>checkpoint,{:.1f},{:.1f}'.format(cp['deltaST'], timeout)
            self.insert_event(event)
        return ok

    def newThermocoupleControlTransition(self):
        desc = {}
        option.ao(desc, 'target', 'Float', name=_("Target Sample Thermocouple Weight"),
                  current=1, min=0, max=1, step=0.01)
        option.ao(desc, 'rate', 'Float', name=_("Control temperature switching rate (0=sudden)"),
                  unit='celsius/minute', current=5, min=0, max=30, step=0.1)
        cp = option.ConfigurationProxy({'self': desc})
        chk = conf.InterfaceDialog(cp, cp, desc, parent=self)
        chk.setWindowTitle(_("Thermocouple Control Transition Configuration"))
        ok = chk.exec_()
        if ok:
            event = '>tctrans,{:.2f},{:.1f}'.format(cp['target'], cp['rate'])
            self.insert_event(event)
        return ok

    def newParam(self):
        # TODO: param window
        assert False, 'TODO'

    def delRow(self):
        crow = self.selection.currentIndex().row()
        if crow <= 1:
            crow = 1
        self.model().removeRows(crow)


class ThermalCycleDesigner(QtGui.QSplitter):

    """The configuration interface widget. It builds interactive controls to deal with a misura configuration object (options, settings, peripherals configurations, etc)."""

    def __init__(self, remote, active_instrument, parent=None, force_live=False):
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
            self.editMenu.addAction(_('Insert checkpoint'), self.table.newCheckpoint)
            self.editMenu.addAction(_('Insert movement'), self.table.newMove)
            self.editMenu.addAction(_('Insert control transition'), self.table.newThermocoupleControlTransition)
            a = self.editMenu.addAction(
                'Insert parametric heating', self.table.newParam)
            a.setEnabled(False)
            self.editMenu.addAction('Remove current row', self.table.delRow)
            self.addButtons()

        self.plot = ThermalCyclePlot()
        self.connect(self.model, QtCore.SIGNAL(
            "dataChanged(QModelIndex,QModelIndex)"), self.replot)
        self.addTable()

        self.main_layout.addWidget(self.table)

        if active_instrument.measure.has_key('onKilnStopped'):
            self.on_kiln_stopped_widget = widgets.build(
                active_instrument, active_instrument.measure, active_instrument.measure.gete('onKilnStopped'))
            self.on_kiln_stopped_widget.button.hide()
            self.on_kiln_stopped_widget.lay.insertWidget(
                0, self.on_kiln_stopped_widget.label_widget)
            self.main_layout.addWidget(self.on_kiln_stopped_widget)

        self.main_layout.addWidget(self.plot)

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
        self.tcc = widgets.ThermalCycleChooser(self.remote, parent=self)
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
