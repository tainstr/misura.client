#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from .. import _
from misura.canon import option
from misura.canon.csutil import next_point, decode_cool_event
from .. import conf
from .. import units
from PyQt4 import QtGui, QtCore

import row
from model import ThermalCurveModel
from delegate import ThermalPointDelegate


def flash_is_available(kiln):
    return kiln.has_key('flash') and kiln['flash']

def motor_is_available(kiln):
    return flash_is_available(kiln) and not (kiln["motor"][0] == "None")

class ThermalCurveTable(QtGui.QTableView):

    """Table view of a thermal cycle."""

    def __init__(self, remote, parent=None, is_live=True):
        QtGui.QTableView.__init__(self, parent)
        self.curveModel = ThermalCurveModel(remote, is_live=is_live)
        self.setModel(self.curveModel)
        self.setItemDelegate(ThermalPointDelegate(remote, self))
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'),
            self.showMenu)


        if is_live:
            self.menu = QtGui.QMenu(self)
            m = self.menu
            m.addAction(_('Insert point'), self.newRow)
            m.addAction(_('Insert checkpoint'), self.newCheckpoint)
            m.addAction(_('Insert natural cooling'), self.newCool)

            if motor_is_available(remote):
                m.addAction(_('Insert movement'), self.newMove)
            if flash_is_available(remote):
                m.addAction(_('Insert control transition'), self.newThermocoupleControlTransition)
            m.addAction(_('Remove current row'), self.delRow)
            m.addSeparator()
        self.resizeColumnsToContents()



    def enable(self, enabled):
        self.menu.setEnabled(enabled)
        edit_trigger = QtGui.QTableView.AllEditTriggers if enabled else QtGui.QTableView.NoEditTriggers
        self.setEditTriggers(edit_trigger)

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
        timeout = 0
        if ent is not False:
            t = ent[0]
        if event.startswith('>cool'):
            T, timeout = decode_cool_event(event)
            print 'insert_event cool', t, timeout
            if timeout > 0:
                t += timeout / 60.
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
        crow = self.selection.currentIndex().row()
        if crow == 0:
            QtGui.QMessageBox.warning(self, _('Impossible event requested'),
                                      _('Cannot insert a checkpoint event as first row'))
            return False
        elif isinstance(self.model().dat[crow][1], basestring):
            # Currently unsupported
            QtGui.QMessageBox.warning(self, _('Impossible event requested'),
                                      _('Cannot insert a checkpoint event after another event'))
            return False
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

    def newCool(self):
        desc = {}

        current_row = self.selection.currentIndex().row()
        previous_row = row.previous_not_event_row_index(current_row + 1, self.model().dat)
        previous_temperature = self.model().dat[previous_row][1]

        option.ao(desc, 'target', 'Float', name=_("Target cooling temperature"),
                  unit='celsius', current=50, min=0, max=previous_temperature, step=0.1)
        option.ao(desc, 'timeout', 'Float', name=_("Timeout (<=0 means forever)"),
                  unit='minute', current=-1, min=-1, max=1e3, step=0.1)
        cp = option.ConfigurationProxy({'self': desc})
        chk = conf.InterfaceDialog(cp, cp, desc, parent=self)
        chk.setWindowTitle(_("Natural cooling configuration"))
        ok = chk.exec_()
        if ok:
            timeout = units.Converter.convert('minute', 'second', cp['timeout'])
            if timeout < 0:
                timeout = -1
            event = '>cool,{:.1f},{:.1f}'.format(cp['target'], timeout)
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
