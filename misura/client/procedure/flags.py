#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore
import row
import collections

def execute(thermal_curve_model, index, is_live=True):
    row_index = index.row()
    column_index = index.column()

    modes_dict = collections.defaultdict(bool)
    modes_dict[row.colTIME] = 'points'
    modes_dict[row.colRATE] = 'ramp'
    modes_dict[row.colDUR] = 'dwell'

    if not index.isValid() or not is_live:
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    current_row_mode = thermal_curve_model.row_modes[row_index]
    current_column_mode = modes_dict[column_index]

    if (thermal_curve_model.dat[row_index][row.colTIME] < 0 and column_index != row.colTEMP) or (row_index == 0 and column_index != row.colTEMP):
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    if (row_index > 0 and column_index == row.colTEMP and thermal_curve_model.dat[row_index][row.colRATE] == 0):
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    if (current_row_mode != current_column_mode and column_index != row.colTEMP):
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
