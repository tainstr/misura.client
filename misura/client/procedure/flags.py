#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore
import row

def execute(thermal_curve_model, index, is_live=True):
    row_index = index.row()
    column_index = index.column()

    if not index.isValid() or not is_live:
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    if (thermal_curve_model.dat[row_index][0] < 0 and column_index != 1) or (row_index == 0 and column_index != row.colTEMP):
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    if (row_index > 0 and column_index == row.colTEMP and thermal_curve_model.dat[row_index][row.colRATE] == 0):
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled)

    return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
