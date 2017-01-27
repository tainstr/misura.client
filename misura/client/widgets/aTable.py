#!/usr/bin/python
# -*- coding: utf-8 -*-
from functools import partial
import os

from .. import _
from misura.client.widgets.active import *
from misura.client import units
from misura.client.clientconf import settings

def _export(loaded, get_column_func, 
            path='/tmp/misura/m.csv', 
            order=False, sep=';\t', header=False):
    """Export to csv file `path`, following column order `order`, using separator `sep`,
    prepending `header`"""
    # Terrible way of reordering!
    logging.debug('ordering', loaded, order)
    if order is not False:
        ordered = [None] * len(loaded)
        for i, j in order.iteritems():
            ordered[j] = loaded[i]
        for i in range(ordered.count(None)):
            ordered.remove(None)
    else:
        ordered = loaded[:]
    logging.debug('ordered', ordered)
    n = len(ordered)
    if not n:
        logging.debug('No columns to export.')
        return False
    f = open(path, 'w')
    if header:
        f.write(header + '\n')
    msg = ('{}' + sep) * len(ordered) + '\n'
    ch = [str(h).replace('summary/', '').replace('\n', '_') for h in ordered]
    f.write(msg.format(*ch))
    dat = []
    nmax = 0
    for h in ordered:
        d = get_column_func(h)
        if len(d) > nmax:
            nmax = len(d)
        dat.append(d)

    def get(v, i):
        if i >= len(v):
            return v[-1]
        return v[i]
    i = 0
    while i < nmax:
        vals = [get(v, i) for v in dat]
        f.write(msg.format(*vals))
        i += 1
    f.close()

def table_model_export(loaded, get_column_func, model, header_view):
    """Prepare to export to CSV file"""
    # TODO: produce a header section based on present samples' metadata
    d = settings.value('/FileSaveToDir', os.path.expanduser('~'))
    path = os.path.join(str(d), 'export.csv')
    dest = str(QtGui.QFileDialog.getSaveFileName(
        header_view, "Export To CSV...", path))
    if dest == '':
        return
    if not dest.lower().endswith('.csv'):
        dest += '.csv'
    # Compute visual index order mapping to logical index,
    # as a consequence of visually moving columns
    order = {}
    for logicalIndex in range(model.columnCount(header_view.currentIndex())):
        if header_view.isSectionHidden(logicalIndex):
            continue
        order[logicalIndex] = header_view.visualIndex(logicalIndex)
    _export(loaded, get_column_func, path=dest, order=order)

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
    view_units = True

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
            if self.csunit!='None' and self.view_units:
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
    
    def trigger_view_units(self, status):
        self.view_units = status
        QtCore.QAbstractTableModel.reset(self) 
        
        
    def make_visible_units_action(self, menu):
        act = menu.addAction(_('Visible units'))
        act.setCheckable(True)
        act.setChecked(self.view_units)
        act.triggered.connect(self.trigger_view_units)
        return act
    
    def make_unit_menu(self, menu, col):
        """Adds a submenu allowing to choose column unit"""
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
        m = menu.addMenu(_('Unit'))
        self.make_visible_units_action(m)
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
    
    _menu_funcs = [] # Keep references for partial functions
    def make_visibility_action(self, menu, col, name=False):
        if not name:
            name = self.header[col][0]
        act = menu.addAction(name)
        f = functools.partial(self.change_visibility, col)
        act.triggered.connect(f)
        act.setCheckable(True)
        act.setChecked(self.visible[col])
        self._menu_funcs.append(f)
        return act
    
    def change_visibility(self, col, status=True):
        """Hide/show `col` according to `status`"""
        self.visible[col] = status
        self.tableObj.table.update_visible_columns()
    
    def make_add_columns_menu(self, menu):
        """Adds a submenu allowing to choose visible/hidden columns"""
        m = menu.addMenu(_('More'))
        for col, vis in enumerate(self.visible):
            if vis:
                continue
            self.make_visibility_action(m, col)
        return m
        
    
    def make_header_menu(self, col):
        """Build table header context menu for `col`"""
        self._menu_funcs = []
        menu = QtGui.QMenu(self.tableObj)
        self.make_visibility_action(menu, col, name=_('Visible'))
        self.make_add_columns_menu(menu)
        self.make_unit_menu(menu, col)
        return menu
            
    def change_unit(self, col, to_unit):
        self.csunit[col] = to_unit
        
    @property
    def visible_indexes(self):
        """Return a list of visible column indexes"""
        r = []
        for i, v in enumerate(self.visible):
            if v: 
                r.append(i)
        return r

class ColHead(object):
    def __init__(self, index, name):
        self.name = name
        self.index = index
    def __str__(self):
        return self.name
    
class ZoomAction(QtGui.QWidgetAction):
    def __init__(self, parent=None):
        QtGui.QWidgetAction.__init__(self, parent)
        self.w = QtGui.QWidget()
        self.lay = QtGui.QVBoxLayout()
        self.w.setLayout(self.lay)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, parent=parent)
        self.slider.setMaximum(100)
        self.slider.setMinimum(0)
        self.slider.setValue(50)
        self.lay.addWidget(self.slider)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.setDefaultWidget(self.w)
        


class aTableView(QtGui.QTableView):

    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.ref_font_size = self.font().pointSize()
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
        self.horizontalHeader().setMovable(True)
        
        self.menu = QtGui.QMenu(self)
        self.rowAfter = partial(self.addRow, 1)
        self.rowBefore = partial(self.addRow, -1)
        self.menu.addAction(_('Add row after'), self.rowAfter)
        self.menu.addAction(_('Add row before'), self.rowBefore)
        self.menu.addAction(_('Delete row'), self.remRow)
        self.menu.addSeparator()
        self.menu.addAction(_('Update'), self.tableObj.get)
        self.menu.addAction(_('Export'), self.export)
        
        self.menu_zoom = self.menu.addMenu(_('Zoom'))
        self.act_zoom = ZoomAction(self.menu_zoom)
        self.act_zoom.slider.valueChanged.connect(self.set_zoom)
        self.menu_zoom.addAction(self.act_zoom)
        
        self.model().make_visible_units_action(self.menu)
        self.model().make_add_columns_menu(self.menu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.update_visible_columns()
        

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))
        
        
    def showHeaderMenu(self, pt):
        column = self.horizontalHeader().logicalIndexAt(pt.x())
        # show menu about the column
        menu = self.model().make_header_menu(column)
        menu.addAction(_('Export'), self.export)
        if not menu:
            logging.debug('No menu for column', column)
            return False
        menu.popup(self.horizontalHeader().mapToGlobal(pt))
    
    def export(self):
        """Export to CSV file"""
        model = self.model()            
        def get_column_func(head):
            index = head.index
            print 'get_column_func', head, index, len(model.rows)
            return [row[index] for row in model.rows]
        h  = self.horizontalHeader()
        loaded = [ColHead(i, name[0]) for i, name in enumerate(model.header)]
        table_model_export(loaded, get_column_func, model, h)
        

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
    
    def set_zoom(self, val):
        val = self.ref_font_size*(1+((val - 50)/100.))
        d = '{{ font-size: {:.0f}pt; selection-background-color: red; }}'.format(val)
        s = 'QTableView '+d
        s += '\n' + 'QHeaderView '+d
        self.setStyleSheet(s)
        self.resizeRowsToContents()
        self.resizeColumnsToContents()

class aTable(ActiveWidget):

    def __init__(self, server, path, prop,  *a, **kw):
        self.initializing = True
        ActiveWidget.__init__(self, server, path, prop, *a, **kw)
        self.table = aTableView(self)
        self.lay.addWidget(self.table)
        self.initializing = False
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        self.table.setSizePolicy(self.sizePolicy())
        
        self.resize_height()
    
    def resizeEvent(self, event):
        if self.parent():
            self.setMinimumWidth(self.parent().width()-50)
        return QtGui.QWidget.resizeEvent(self, event) 
            
    
    def resize_height(self):
        h = self.table.resize_height()
        self.setMinimumHeight(h)

    def update(self):
        if self.initializing:
            return
        self.table.up()
        self.resize_height()
        
