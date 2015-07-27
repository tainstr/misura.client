#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from misura.client.widgets.active import *
from functools import partial


class aTablePointDelegate(QtGui.QItemDelegate):

    """Delegato per la modifica delle celle in una tabella"""

    def __init__(self, parent=None):
        QtGui.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        mod = index.model()
        col = index.column()
        colType = mod.header[col][1]
        logging.debug('%s', colType)
        if colType == 'Float':
            wg = QtGui.QDoubleSpinBox(parent)
            # TODO: implementare Range e altri argomenti opzionali per colonna.
            wg.setRange(-1e32, 1e32)
#			wg.setSuffix(u' \xb0C')
        elif colType == 'Integer':
            wg = QtGui.QSpinBox(parent)
            wg.setRange(-2147483647, 2147483647)
            logging.debug(
                '%s %s %s', 'Created QSpingBox', wg.maximum(), wg.minimum())
        elif colType == 'String':
            wg = QtGui.QLineEdit(parent)
        elif colType == 'Boolean':
            wg = QtGui.QCheckBox(parent)
            wg.setTristate(False)
        else:
            wg = QtGui.QItemDelegate.createEditor(self, parent, option, index)
        return wg

    def setEditorData(self, editor, index):
        mod = index.model()
        col = index.column()
        colType = mod.header[col][1]
        logging.debug('%s', colType)
        if colType in ['Float', 'Integer']:
            val = mod.data(index)
            editor.setValue(val)
        elif colType == 'String':
            val = mod.data(index)
            editor.setText(val)
        elif colType == 'Boolean':
            if index.row() == 0:
                return
            val = mod.data(index)
            if val == 'True':
                editor.setCheckState(2)
            else:
                editor.setCheckState(0)
        else:
            QtGui.QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        col = index.column()
        colType = model.header[col][1]
        logging.debug('%s', colType)
        if colType in ['Float', 'Integer']:
            val = editor.text()
            val = editor.valueFromText(val)
            model.setData(index, val, QtCore.Qt.DisplayRole)
        elif colType == 'Boolean':
            if index.row() == 0:
                return
            val = editor.checkState()
            if val:
                val = 'True'
            else:
                val = ''
            model.setData(index, val)
        elif colType == 'String':
            val = editor.text()
            model.setData(index, val)
        else:
            QtGui.QItemDelegate.setModelData(self, editor, model, index)


class aTableModel(QtCore.QAbstractTableModel):

    def __init__(self, tableObj):
        QtCore.QAbstractTableModel.__init__(self)
        self.tableObj = tableObj
        self.rows = []
        self.header = []
        self.up()

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.rows)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.header)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        row = self.rows[index.row()]
        col = index.column()
        if role != QtCore.Qt.DisplayRole:
            return
        val = row[col]
        return val

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            logging.debug('%s', self.header)
            return self.header[section][0]

    def up(self):
        hp = self.tableObj.get()
        # Table header is the first row in the property
        self.header = hp[0]
        # Rows are the rest of the property
        self.rows = hp[1:]
        QtCore.QAbstractTableModel.reset(self)

    def emptyRow(self):
        """Create a valid empty row for addition"""
        row = []
        for ent in self.header:
            ent = ent[1]
            if ent == 'String':
                row.append('')
            elif ent in ['Float', 'Integer']:
                row.append(0)
            else:
                row.append('')
        return row

    def flags(self, index):
        return QtCore.Qt.ItemFlags(QtCore.QAbstractTableModel.flags(self, index) | QtCore.Qt.ItemIsEditable)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        irow = index.row()
        icol = index.column()
        colType = self.header[icol][1]
        row = self.rows[irow]
        if colType == 'Boolean':
            s = value.toBool()
            s = s == True
            row[icol] = s
        elif colType == 'Float':
            row[icol] = float(value)
        elif colType == 'Integer':
            row[icol] = int(value)
        elif colType == 'String':
            row[icol] = str(value)
        # Sostituisco la riga:

        self.rows[irow] = row
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.index(irow, 0),
                  self.index(self.rowCount(), self.columnCount()))
        self.apply()
        return True

    def apply(self):
        self.tableObj.set([self.header] + self.rows)
        self.up()


class aTableView(QtGui.QTableView):

    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.curveModel = aTableModel(parent)
        self.setModel(self.curveModel)
        self.setItemDelegate(aTablePointDelegate(self))
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.menu = QtGui.QMenu(self)
        self.rowAfter = partial(self.addRow, 1)
        self.rowBefore = partial(self.addRow, -1)
        self.menu.addAction(_('Add row after'), self.rowAfter)
        self.menu.addAction(_('Add row before'), self.rowBefore)
        self.menu.addAction(_('Delete row'), self.remRow)
        self.menu.addSeparator()
        self.menu.addAction(_('Update'), self.curveModel.up)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))

    def addRow(self, pos=0):
        model = self.model()
        new = model.emptyRow()
        i = self.currentIndex().row()
        if pos == 0:  # At the end
            model.rows.append(new)
        elif pos == 1:  # After current
            model.rows = model.rows[:i + 1] + [new] + model.rows[i + 1:]
        elif pos == -1:  # Before current
            model.rows = model.rows[:i] + [new] + model.rows[i:]
        model.apply()

    def remRow(self):
        model = self.model()
        i = self.currentIndex().row()
        model.apply()


class aTable(ActiveWidget):

    def __init__(self, server, path, prop,  parent=None):
        self.initializing = True
        ActiveWidget.__init__(self, server, path, prop, parent)
        self.table = aTableView(self)
        self.lay.addWidget(self.table)
        self.initializing = False

    def update(self):
        if self.initializing:
            return
        self.table.model().up()
