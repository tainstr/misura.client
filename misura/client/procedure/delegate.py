#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from .. import parameters as params
from PyQt4 import QtGui, QtCore
import row

from time_spinbox import TimeSpinBox


class ThermalPointDelegate(QtGui.QItemDelegate):

    """Delegate for thermal cycle table cells"""

    def __init__(self, remote, parent=None):
        self.remote = remote
        QtGui.QItemDelegate.__init__(self, parent)

    def timeLimits(self, index):
        pre = index.model().index(index.row() - 1, row.colTIME)
        pre = index.model().data(pre)
        post = index.model().index(index.row() + 1, row.colTIME)
        post = index.model().data(post)
        if post == 0:
            post = params.MAX
        return pre, post

    def createEditor(self, parent, option, index):
        mod = index.model()
        val = mod.data(index)
        wg = QtGui.QItemDelegate.createEditor(self, parent, option, index)
        if index.column() == row.colTIME:
            mod.mode_points(index.row())
            if index.row() == 0:
                return QtGui.QLabel('Initial Time', parent)
            wg = TimeSpinBox(parent)
            pre, post = self.timeLimits(index)
            if val < 0:
                wg.setReadOnly()
            else:
                wg.setRange(pre, post)
        elif index.column() == row.colTEMP:
            if isinstance(val, basestring):
                # Read-only events
                return None

            wg = QtGui.QDoubleSpinBox(parent)

            maxControlTemp = self.remote['maxControlTemp']

            wg.setRange(0, maxControlTemp)
            wg.setSuffix(u' \xb0C')

        elif index.column() == row.colRATE:
            mod.mode_ramp(index.row())
            if index.row() == 0:
                return QtGui.QLabel('undefined', parent)
            wg = QtGui.QDoubleSpinBox(parent)
            
            maxHeatingRate = self.remote['maxHeatingRate']
            wg.setRange(-500, maxHeatingRate)

            wg.setSuffix(u' \xb0C/min')
        elif index.column() == row.colDUR:
            mod.mode_dwell(index.row())
            if index.row() == 0:
                return QtGui.QLabel('undefined', parent)
            wg = TimeSpinBox(parent)
            wg.setRange(0, params.MAX)

        return wg

    def setEditorData(self, editor, index):
        # First row is not editable
        col = index.column()
        if index.row() == 0 and col in [row.colTIME]:
            logging.debug('row0 is not editable')
            return
        mod = index.model()
        val = mod.data(index)
        if row.colTIME <= col <= row.colDUR:
            if hasattr(editor, 'setValue'):
                editor.setValue(val)
            else:
                editor.setText(val)
        else:
            QtGui.QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        col = index.column()
        # first row is not editable
        if index.row() == 0 and col != row.colTEMP:
            logging.debug('setModelData: First row is not editable', index.row(), index.column())
            return
        val = None
        if hasattr(editor, 'value'):
            val = editor.value()
            logging.debug('editor value', val)
        elif hasattr(editor, 'text'):
            val = editor.text()
            logging.debug('editor text', val)
            if hasattr(editor, 'valueFromText'):
                val = editor.valueFromText(val)
                logging.debug('editor valueFromText', val)
        if val is not None:
            logging.debug('setModelData', val, index.row(), index.column())
            model.setData(index, val, QtCore.Qt.DisplayRole)
        else:
            QtGui.QItemDelegate.setModelData(self, editor, model, index)

