#!/usr/bin/python
# -*- coding: utf-8 -*-
from functools import partial
import os
import io

import numpy as np

from .. import _
from misura.client.widgets.active import *
from misura.client import units
from misura.client import iutils
from misura.client.clientconf import settings
from . import builder

def _export(loaded, get_column_func,
            path='/tmp/misura/m.csv',
            order=False, sep=';\t', header=False,
            get_unit_func=False,
            get_verbose_func=False):
    """Export `loaded` column names to csv file `path`, following column order `order`, using separator `sep`,
    prepending `header`. Use `get_column_func` to retrieve the dataset values for each column name."""
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
    f = io.open(path, 'w', encoding="utf-8")
    # Write custom header
    if header:
        f.write(header + '\n')
        
    # Write names header
    
    msg = unicode(('{}' + sep) * len(ordered) + '\n')
    ch = [str(h).replace('summary/', '').replace('\n', '_') for h in ordered]
    f.write(msg.format(*ch))
    
    # Write optional headers
    for hfunc in (get_unit_func, get_verbose_func):
        if not hfunc:
            continue
        ch = [unicode(hfunc(h)) for h in ordered]
        s = msg.format(*ch)
        f.write(s)
    
    
        
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


def table_model_export(loaded, get_column_func, model, header_view, 
                       get_unit_func=False,
                       get_verbose_func=False):
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
    _export(loaded, 
            get_column_func, 
            path=dest, 
            order=order, 
            get_unit_func=get_unit_func,
            get_verbose_func=get_verbose_func)


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
            if p==0: p=2
            dc = extend_decimals(val, p)
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
        if colType == 'Float':
            val = float(mod.data(index))
            editor.setValue(val)
        elif colType == 'Integer':
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
            print 'setting model data', val
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
    _rotated = False
    perpendicular_header_col = -1
    sigOutdated = QtCore.pyqtSignal()

    def __init__(self, tableObj):
        QtCore.QAbstractTableModel.__init__(self)
        self.tableObj = tableObj
        self.rows = []
        self.header = []
        self.visible_headers = []  # visible headers
        self.visible_data = []  # visible data rows
        self.unit = 'None'
        self.csunit = 'None'
        self.precision = 'None'
        self.up()

    def rowCount(self, index=QtCore.QModelIndex()):
        if self.rotated:
            return len(self.header)
        return len(self.rows)

    def columnCount(self, index=QtCore.QModelIndex()):
        if self.rotated:
            return len(self.rows)
        return len(self.header)
    
    def raw_value(self, col, row):
        row = self.rows[row]
        val = row[col]
        return val
    
    def format_data(self, col, row):
        val = self.raw_value(col, row)
        if val is None:
            return None
        # handle conversion from option unit to client-side unit
        if self.unit != 'None' and self.csunit != 'None':
            u, cu = self.unit[col], self.csunit[col]
            if u != cu:
                val = units.Converter.convert(u, cu, val)
        if self.precision != 'None':
            p = self.precision
            if hasattr(p, '__len__'):
                p = p[col]
            dc = extend_decimals(val, p)
            ps = '{:.' + str(dc) + 'f}'
            val = ps.format(val)
        return val

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        row = index.row()
        col = index.column()
        if self.rotated:
            a = col
            col = row
            row = a
        if role == QtCore.Qt.DecorationRole:
            if self.header[col][1]!='Boolean':
                return
            if self.raw_value(col, row):
                icon = iutils.theme_icon('dialog-ok')
            else:
                icon = iutils.theme_icon('edit-delete')
            return icon.pixmap(32,32)
            
        if role != QtCore.Qt.DisplayRole:
            return
        if self.header[col][1]=='Boolean':
            return
        return self.format_data(col, row)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return
        if self.rotated:
            if orientation == QtCore.Qt.Horizontal:
                if self.perpendicular_header_col < 0:
                    return None
                else:
                    return self.format_data(self.perpendicular_header_col, section)
        else:
            if orientation == QtCore.Qt.Vertical:
                if self.perpendicular_header_col < 0:
                    return None
                else:
                    return self.format_data(self.perpendicular_header_col, section)

        label = self.header[section][0]
        unit = False
        if self.csunit != 'None' and self.view_units and len(self.csunit)>section:
            u = self.csunit[section]
            unit = units.hsymbols.get(u, False)
        if unit:
            label += u' ({})'.format(unit)
        return label

    def validate(self):
        """Validate model consistency"""
        N = len(self.header)
        v = len(self.visible_headers) == N
        v = v and (len(self.visible_rows) == len(self.rows))
        if v and self.unit:
            v = len(self.unit) == N
        if v and self.precision != 'None':
            v = len(self.precision) == N
        if v and self.csunit != 'None':
            v = len(self.csunit) == N
        if not v:
            logging.error(
                'aTableModel data is outdated!', self.tableObj.handle)
        return v

    def up(self, validate=True):
        r = self._rotated
        self._rotated = False
        hp = self.tableObj.current
        # Table header is the first row in the option
        self.header = hp[0]
        # Rows are the rest of the option
        self.rows = hp[1:]
        self.unit = self.tableObj.prop.get('unit', False)
        if self.unit:
            if self.csunit == 'None' or len(self.csunit) != len(self.unit):
                self.csunit = self.unit[:]
        self.precision = self.tableObj.prop.get('precision', 'None')
        self.visible_data = [1] * len(self.rows)
        self.visible_headers = self.tableObj.prop.get(
            'visible', [1] * len(self.header))
        v = self.validate()
        if validate and not v:
            self.tableObj.update_option()
            self.up(validate=False)
        self._rotated = r
        QtCore.QAbstractTableModel.reset(self)
        return v

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
        if self.rotated:
            a = icol
            icol = irow
            irow = a
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
        if self.unit != 'None' and self.csunit != 'None':
            u, cu = self.unit[icol], self.csunit[icol]
            if u != cu:
                value = units.Converter.convert(cu, u, value)
        row[icol] = value
        self.rows[irow] = row
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.index(irow, 0),
                  self.index(self.rowCount(), self.columnCount()))
        self.apply()
        return True

    def apply(self):
        self.tableObj.remObj.set(
            self.tableObj.handle,  [self.header] + self.rows)

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
        if self.unit == 'None':
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
            a.setChecked(to_unit == cu)
        return m

    _menu_funcs = []  # Keep references for partial functions

    def make_visibility_action(self, menu, col, orientation, name=False):
        if not name:
            name = self.headerData(col, orientation)
        if not name:
            name = str(col)

        act = menu.addAction(name)
        f = functools.partial(self.change_visibility, col, orientation)
        act.triggered.connect(f)
        act.setCheckable(True)
        if orientation == QtCore.Qt.Horizontal:
            act.setChecked(self.visible_cols[col])
        else:
            act.setChecked(self.visible_rows[col])
        self._menu_funcs.append(f)
        return act

    @property
    def visible_cols(self):
        if self.rotated:
            return self.visible_data
        else:
            return self.visible_headers

    @visible_cols.setter
    def visible_cols(self, new):
        if self.rotated:
            self.visible_data = new
        else:
            self.visible_headers = new

    def set_visible_col(self, col, status):
        if self.rotated:
            self.visible_data[col] = status
        else:
            self.visible_headers[col] = status

    @property
    def visible_rows(self):
        if self.rotated:
            return self.visible_headers
        else:
            return self.visible_data

    @visible_rows.setter
    def visible_rows(self, new):
        if self.rotated:
            self.visible_headers = new
        else:
            self.visible_data = new

    def set_visible_row(self, row, status):
        if self.rotated:
            self.visible_headers[row] = status
        else:
            self.visible_data[row] = status

    @property
    def rotated(self):
        return self._rotated

    @rotated.setter
    def rotated(self, new):
        self._rotated = new

    def change_visibility(self, col, orientation, status=True):
        """Hide/show `col` according to `status`"""
        if orientation == QtCore.Qt.Horizontal:
            self.set_visible_col(col, status)
        else:
            self.set_visible_row(col, status)
        self.tableObj.table.update_visible_columns()

    def make_visibility_menu(self, menu, orientation):
        """Adds a submenu allowing to choose visible/hidden columns"""
        if orientation == QtCore.Qt.Vertical:
            m = menu.addMenu(_('More rows'))
            v = self.visible_rows
        else:
            m = menu.addMenu(_('More columns'))
            v = self.visible_cols
        for col, vis in enumerate(v):
            if vis:
                continue
            self.make_visibility_action(m, col, orientation)
        return m

    def set_as_perpendicular_header(self, col):
        if self.perpendicular_header_col == col:
            col = -1
        self.perpendicular_header_col = col
        QtCore.QAbstractTableModel.reset(self)
        self.emit(QtCore.SIGNAL('layoutChanged()'))
        self.tableObj.resize_height()

    def make_perpendicular_header_action(self, menu, col):
        f = functools.partial(self.set_as_perpendicular_header, col)
        act = menu.addAction(_('Use as header'), f)
        act.setCheckable(True)
        act.setChecked(self.perpendicular_header_col == col)
        return act

    def make_header_menu(self, col, orientation):
        """Build table header context menu for `col`"""
        self.validate()
        self._menu_funcs = []
        menu = QtGui.QMenu(self.tableObj)
        self.make_visibility_action(menu, col, orientation, name=_('Visible'))
        self.make_visibility_menu(menu, orientation)
        self.make_unit_menu(menu, col)
        self.make_perpendicular_header_action(menu, col)
        return menu

    def change_unit(self, col, to_unit):
        self.csunit[col] = to_unit

    @property
    def visible_indexes(self):
        """Return a list of visible column indexes"""
        #TODO: expand to consider row visibility
        r = []
        for i, v in enumerate(self.visible_cols):
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
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        if self.tableObj.readonly:
            self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        for h, d in ((self.horizontalHeader(), QtCore.Qt.Horizontal),
                     (self.verticalHeader(), QtCore.Qt.Vertical)):
            h.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            h.customContextMenuRequested.connect(
                functools.partial(self.showHeaderMenu, h, d))
            h.setMovable(True)

        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.update_visible_columns()

    @property
    def main_header(self):
        return self.verticalHeader() if self.rotated else self.horizontalHeader()

    @property
    def rotated(self):
        return self.model().rotated

    def showMenu(self, pt):
        index = self.indexAt(pt)
        menu = QtGui.QMenu(self)
        self.rowAfter = partial(self.addRow, 1)
        self.rowBefore = partial(self.addRow, -1)
        if not self.tableObj.readonly:
            menu.addAction(_('Add row after'), self.rowAfter)
            menu.addAction(_('Add row before'), self.rowBefore)
            menu.addAction(_('Delete row'), self.remRow)
        menu.addSeparator()

        menu.addAction(_('Update'), self.tableObj.get)
        menu.addAction(_('Export'), self.export)
        self.make_rotation_action(menu)
        menu_zoom = menu.addMenu(_('Zoom'))
        act_zoom = ZoomAction(menu_zoom)
        act_zoom.slider.valueChanged.connect(self.set_zoom)
        menu_zoom.addAction(act_zoom)
        self.model().make_visible_units_action(menu)
        self.model().make_visibility_menu(menu, QtCore.Qt.Horizontal)
        self.model().make_visibility_menu(menu, QtCore.Qt.Vertical)
        # View local aggregation
        if self.tableObj.prop.get('aggregate', ''):
            self.make_aggregation_menu(index, menu)

        menu.popup(self.mapToGlobal(pt))

    def make_rotation_action(self, menu):
        self.act_rotate = menu.addAction(_('Rotate'), self.rotate)
        self.act_rotate.setCheckable(True)
        self.act_rotate.setChecked(self.rotated)

    def make_aggregation_menu(self, index, menu):
        if self.model().data(index) is None:
            logging.debug('Empty cell')
            return menu
        dev, t, targets_map = self.aggregate_cell_source(index)
        root = dev.root
        dmenu = builder.build_aggregation_menu(
            root, dev, menu, target=t, win_map=self.tableObj._win_map)
        # See if target option is an aggregation in its turn
        p = dev.gete(t)
        aggregation = p.get('aggregate', '')
        if aggregation:
            builder.build_recursive_aggregation_menu(root, dev, aggregation,
                                                     targets_map, dmenu, win_map=self.tableObj._win_map)

        return menu

    def _coord(self, index):
        """Return col, row considering rotation"""
        col = index.column()
        row = index.row()
        if self.rotated:
            a = row
            row = col
            col = a
        return col, row

    def aggregate_cell_source(self, index):
        """Returns the aggregation source device and option name for cell at `index`"""
        wg = self.tableObj
        r = wg.remObj.collect_aggregate(wg.prop['aggregate'], wg.handle)
        func_name, targets, values, fullpaths, foo = r
        col0, row0 = self._coord(index)
        targets_map = {}
        col = col0
        row = row0
        j = 0
        j0 = 0
        is_merge_tables = func_name == 'merge_tables'
        found = not is_merge_tables
        # Resolve merge_tables shape
        for target_index, target in enumerate(targets):
            if found:  # or not a merge_tables
                break
            for device_index, value in enumerate(values[target]):
                j0 = j
                if not hasattr(value, '__len__'):
                    j += 1
                elif not hasattr(value[0], '__len__'):
                    j += 1
                else:
                    # Table header length
                    j += len(value[0])
                if j0 <= col < j:
                    col = target_index
                    row = device_index
                    found = True
                    break

        t = targets[col]
        devpath = fullpaths[t][row]
        root = wg.remObj.root
        dev = root.toPath(devpath)

        # Complete targets_map for highlight_option
        targets_map[devpath] = t
        if found and is_merge_tables:
            sub_target_col = col0 - j0
            prop = dev.gete(t)
            agg = prop.get('aggregate', '')
            if agg:
                r = dev.collect_aggregate(agg, t)
                f, targets, values, fullpaths, devs = r
                print targets, sub_target_col, col0, j0
                subt = targets[sub_target_col]
                for fullpath in fullpaths[subt]:
                    targets_map[fullpath] = '#SKIP#'
                targets_map[fullpaths[subt][row0]] = subt

        return dev, t, targets_map

    def showHeaderMenu(self, header, orientation, pt):
        coord = pt.x()
        if orientation == QtCore.Qt.Vertical:
            coord = pt.y()
        column = header.logicalIndexAt(coord)
        # show menu about the column
        menu = self.model().make_header_menu(column, orientation)
        if not menu:
            logging.debug('No menu for column', column, orientation)
            return False
        self.make_rotation_action(menu)
        menu.addAction(_('Export'), self.export)
        menu.addSeparator()
        if not self.tableObj.readonly:
            menu.addAction(_('Add row'), self.addRow)
        
        menu.popup(header.mapToGlobal(pt))

    def export(self):
        """Export to CSV file"""
        model = self.model()

        def get_column_func(head):
            index = head.index
            print 'get_column_func', head, index, len(model.rows)
            return [row[index] for row in model.rows]
        h = self.main_header
        loaded = [ColHead(i, name[0]) for i, name in enumerate(model.header)]
        table_model_export(loaded, get_column_func, model, h)

    def addRow(self, pos=0):
        # TODO: rotation-aware
        model = self.curveModel
        new = model.emptyRow()
        i = self.currentIndex()
        if i:
            i = i.row()
        else:
            i = 0
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
        r = self.model().up()
        if not r:
            # Require a complete redraw
            return False
        self.update_visible_columns()
        return True

    def update_visible_columns(self):
        for i, v in enumerate(self.model().visible_cols):
            self.setColumnHidden(i, not v)
        for i, v in enumerate(self.model().visible_rows):
            self.setRowHidden(i, not v)

    def resize_height(self):
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        h = self.main_header.height()
        for i in range(self.model().rowCount()):
            h += self.rowHeight(i)
        return h

    def set_zoom(self, val):
        val = self.ref_font_size * (1 + ((val - 50) / 100.))
        d = '{{ font-size: {:.0f}pt; }}'.format(
            val)
        s = 'QTableView ' + d
        s += '\n' + 'QHeaderView ' + d
        self.setStyleSheet(s)
        self.resizeRowsToContents()
        self.resizeColumnsToContents()

    def rotate(self):
        self.model().rotated = not self.model().rotated
        self.act_rotate.setChecked(self.model().rotated)
        self.up()
        self.update_visible_columns()
        self.resizeRowsToContents()
        self.resizeColumnsToContents()


class aTable(ActiveWidget):
    table = False

    def redraw(self):
        super(aTable, self).redraw()
        self.table = aTableView(self)
        self.lay.addWidget(self.table)
        self.setSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        self.table.setSizePolicy(self.sizePolicy())
        self.resize_height()
        self.table.model().sigOutdated.connect(self.update_option)

    def resizeEvent(self, event):
        if self.parent():
            self.setMinimumWidth(self.parent().width() - 50)
        return QtGui.QWidget.resizeEvent(self, event)

    def resize_height(self):
        h = self.table.resize_height()
        self.setMinimumHeight(h)

    def update(self):
        if self.table is False:
            return
        self.table.up()
        self.resize_height()
        self.set_enabled()
