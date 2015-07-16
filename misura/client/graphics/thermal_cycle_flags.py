from PyQt4 import QtCore
import thermal_cycle_row

def execute(self, index):
	row_index = index.row()
	column_index = index.column()

	if not index.isValid():
	    return QtCore.Qt.ItemIsEditable

	if (self.dat[row_index][0] < 0 and column_index != 1) or (row_index == 0 and column_index != thermal_cycle_row.colTEMP):
	    return QtCore.Qt.ItemIsEditable

	return QtCore.Qt.ItemFlags(QtCore.QAbstractTableModel.flags(self, index) | QtCore.Qt.ItemIsEditable)