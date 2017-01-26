#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from misura.client.widgets.active import *
from misura.client import units
from functools import partial


class aTablePointDelegate(QtGui.QItemDelegate):

    """Delegato per la modifica delle celle in una tabella"""

    def __init__(self, parent=None):
        QtGui.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        mod = index.model()
        col = index.column()
        p = mod.tableObj.prop.get('precision', 2)
        if hasattr(p, '__len__'):
            p = p[col]
        
        colType = mod.header[col][1]
        if colType == 'Float':
            wg = QtGui.QDoubleSpinBox(parent)
            wg.setRange(MIN, MAX)
            val = float(mod.data(index))
            dc = extend_decimals(val, default=0, extend_by=p+2)
            wg.setDecimals(dc)
        elif colType == 'Integer':
            wg = QtGui.QSpinBox(parent)
            wg.setRange(-2147483647, 2147483647)
            logging.debug('Created QSpingBox', wg.maximum(), wg.minimum())
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
        if colType=='Float':
            val = float(mod.data(index))
            editor.setValue(val)
        elif colType=='Integer':
            val = int(mod.data(index))
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
        if colType in ['Float', 'Integer']:
            val = editor.text()
            val = editor.valueFromText(val)
            print 'setting model data',val
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
        self.visible = []
        self.unit = 'None'
        self.csunit = 'None'
        self.precision = 'None'
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
        # handle conversion from option unit to client-side unit
        if self.unit!='None' and self.csunit!='None':
            u, cu = self.unit[col], self.csunit[col]
            if u!=cu:
                val = units.Converter.convert(u, cu, val)
        if self.precision!='None':
            p = self.precision
            if hasattr(p, '__len__'):
                p = p[col]
            dc = extend_decimals(val, default=0, extend_by=p)
            ps = '{:.'+str(dc)+'f}'
            val = ps.format(val)
        return val

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            label = self.header[section][0]
            unit = False
            if self.csunit!='None':
                unit = units.hsymbols.get(self.csunit[section], False)
            if unit:
                label += u' ({})'.format(unit)
            return label

    def up(self):
        hp = self.tableObj.current
        # Table header is the first row in the option
        self.header = hp[0]
        # Rows are the rest of the option
        self.rows = hp[1:]
        self.unit = self.tableObj.prop.get('unit', False)
        self.precision = self.tableObj.prop.get('precision', 'None')
        self.visible = self.tableObj.prop.get('visible', [1]*len(self.header))
        if self.csunit=='None':
            self.csunit = self.unit[:]
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
            value = s
        elif colType == 'Float':
            value = float(value)
        elif colType == 'Integer':
            value = int(value)
        elif colType == 'String':
            value = str(value)
        # handle conversion from client-side unit to option unit
        if self.unit!='None' and self.csunit!='None':
            u, cu = self.unit[icol], self.csunit[icol]
            if u!=cu:
                value = units.Converter.convert(cu, u, value)
        row[icol] = value
        self.rows[irow] = row
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.index(irow, 0),
                  self.index(self.rowCount(), self.columnCount()))
        self.apply()
        return True

    def apply(self):
        self.tableObj.remObj.set(self.tableObj.handle,  [self.header] + self.rows)
        
    def make_header_menu(self, col):
        if self.unit=='None':
            logging.debug('No unit defined', self.unit)
            return False
        u = self.unit[col]
        if u in ('None', None, False):
            logging.debug('No unit set for col', u, col)
            return False
        dim = units.known_units.get(u, False)
        if not dim:
            logging.debug('Unknown unit:', u)
            return False
        group = units.to_base[dim].keys()
        cu = self.csunit[col]
        m = QtGui.QMenu(self.tableObj)
        self.unit_funcs = []
        for to_unit in group:
            f = functools.partial(self.change_unit, col, to_unit)
            self.unit_funcs.append(f)
            lbl = to_unit
            us = units.hsymbols.get(to_unit, False)
            if us:
                lbl += u' ({})'.format(us)
            a = m.addAction(lbl, f)
            a.setCheckable(True)
            a.setChecked(to_unit==cu)
        return m
            
    def change_unit(self, col, to_unit):
        self.csunit[col] = to_unit


class aTableView(QtGui.QTableView):

    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.tableObj = parent
        self.curveModel = aTableModel(parent)
        self.setModel(self.curveModel)
        self.setItemDelegate(aTablePointDelegate(self))
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        
        self.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.showHeaderMenu)
        
        self.menu = QtGui.QMenu(self)
        self.rowAfter = partial(self.addRow, 1)
        self.rowBefore = partial(self.addRow, -1)
        self.menu.addAction(_('Add row after'), self.rowAfter)
        self.menu.addAction(_('Add row before'), self.rowBefore)
        self.menu.addAction(_('Delete row'), self.remRow)
        self.menu.addSeparator()
        self.menu.addAction(_('Update'), self.tableObj.get)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.update_visible_columns()

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))
        
    def showHeaderMenu(self, pt):
        column = self.horizontalHeader().logicalIndexAt(pt.x())
        # show menu about the column
        menu = self.model().make_header_menu(column)
        if not menu:
            logging.debug('No menu for column', column)
            return False
        menu.popup(self.horizontalHeader().mapToGlobal(pt))
        

    def addRow(self, pos=0):
        model = self.curveModel
        new = model.emptyRow()
        i = self.currentIndex()
        if i:
            i=i.row()
        else:
            i=0
        if pos == 0:  # At the end
            model.rows.append(new)
        elif pos == 1:  # After current
            model.rows = model.rows[:i + 1] + [new] + model.rows[i + 1:]
        elif pos == -1:  # Before current
            model.rows = model.rows[:i] + [new] + model.rows[i:]
        model.apply()

    def remRow(self):
        model = self.curveModel
        i = self.currentIndex().row()
        model.rows.pop(i)
        model.apply()
        
    def up(self):
        self.model().up()
        self.update_visible_columns()
    
    def update_visible_columns(self):
        for i, v in enumerate(self.model().visible):
            self.setColumnHidden(i, not v)

    def resize_height(self):
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        h = self.horizontalHeader().height()
        for i in range(self.model().rowCount()):
            h += self.rowHeight(i)
        self.setMinimumHeight(h)
        return h

class aTable(ActiveWidget):

    def __init__(self, server, path, prop,  parent=None):
        self.initializing = True
        ActiveWidget.__init__(self, server, path, prop, parent)
        self.table = aTableView(self)
        self.lay.addWidget(self.table)
        self.initializing = False
        self.table.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        self.resize_height()
    
    def resize_height(self):
        h = self.table.resize_height()
        self.setMinimumHeight(h)

    def update(self):
        if self.initializing:
            return
        self.table.up()
        self.resize_height()
        
