#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore
import thermal_cycle_row


def execute(thermal_curve_model, index):
    row_index = index.row()
    column_index = index.column()

    if not index.isValid():
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    if (thermal_curve_model.dat[row_index][0] < 0 and column_index != 1) or (row_index == 0 and column_index != thermal_cycle_row.colTEMP):
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    if (row_index > 0 and column_index == thermal_cycle_row.colTEMP and thermal_curve_model.dat[row_index][thermal_cycle_row.colRATE] == 0):
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
