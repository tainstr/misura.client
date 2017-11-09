#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tabular view of data in a MisuraDocument"""
import os
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from .. import iutils, _
import re

from misura.client.widgets import table_model_export
from misura.client import units

# TODO: these functions should be generalized and applied also by the
# navigator. THey should also present data in hierarchy (not plain).
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
voididx = QtCore.QModelIndex()
    

class SummaryModel(QtCore.QAbstractTableModel):
    _rowCount = 0
    _columnCount = 0
    _loaded = []
    auto_load = True

    def __init__(self, *a, **k):
        QtCore.QAbstractTableModel.__init__(self, *a, **k)


    def set_doc(self, doc):
        self.doc = doc
        self._loaded = []
        self._rowCount = 0
        self._columnCount = 0
        self.update()

    def set_loaded(self, loaded):
        if set(loaded) != set(self._loaded):
            self._loaded = loaded
            self.endResetModel()
            return True
        return False

    @property
    def model(self):
        return self.doc.model

    @property
    def tree(self):
        return self.model.tree

    def refresh(self):
        logging.debug('SummaryView.refresh')
        self.model.refresh()
        self.update()
        
    def get_loaded(self):
        ldd = []
        for k, ds in self.doc.data.iteritems():
            if len(ds) > 0:
                ldd.append(k) 
        if self.auto_load:
            self.set_loaded(ldd)
        return ldd       

    def update(self):
        r = False
        # New rows length
        start = self._rowCount
        self.get_loaded()
        end = max([0]+[len(self.doc.data[k].data) for k in self._loaded])
        # Update length
        if end > start:
            logging.debug('SummaryModel.update: inserting rows', start, end)
            self.beginInsertRows(self.index(0, 0), start, end)
            self._rowCount = end
            self.endInsertRows()
            # Maybe a qt bug: this does not work without endResetModel
            self.endResetModel()
        return r

    def columnCount(self, parent):
        self._columnCount = len(self._loaded)
        return self._columnCount

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            return self.humanized_header(self._loaded[section])

    def humanized_header(self, inhuman_header):
        label = getattr(self.doc.data[inhuman_header], "m_label", False)

        if not label:
            return inhuman_header

        regex = re.compile("(^[0-9]+):.*/sample([0-9]+)/")
        matches = regex.match(inhuman_header)

        if not matches:
            return label

        plot_number, sample_number = matches.groups()
        if sample_number != "0":
            label = label + " (%s)" % sample_number

        return label

    def rowCount(self, parent):
        if not self.doc:
            return 0
        self.get_loaded()
        if len(self._loaded) == 0:
            return 0
        if not self.doc.data.has_key(self._loaded[0]):
            return 0
        return self._rowCount

    def data(self, index, role=QtCore.Qt.DisplayRole):
        col = index.column()
        row = index.row()
        if role not in [Qt.DisplayRole, 'data']:
            return None
        h = self._loaded[col]
        ds = self.doc.data[h]
        if row >= len(ds.data):
            return '...'
        val = ds.data[row]
        if role == 'data':
            return val
        s = iutils.num_to_string(val)
        return s



class SummaryHeader(QtGui.QHeaderView):

    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None):
        QtGui.QHeaderView.__init__(self, orientation, parent=parent)
        self.setMovable(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.show_menu)
        self.menu = QtGui.QMenu(self)

    @property
    def tree(self):
        return self.parent().model().tree

    @property
    def treemodel(self):
        return self.parent().model().model

    def hide(self):
        """Hide a column"""
        if not self.point:
            return 'No point for hide()'
        i = self.logicalIndexAt(self.point)
        self.hideSection(i)
        logging.debug('Hide', i)

    def show_more(self):
        """Load more columns from document model"""
        # TODO: load a treeview with checkable items in order to load more
        pass

    def export(self):
        """Export to CSV file"""
        model = self.parent().model()
        def get_column_func(name):
            return model.doc.data[name].data
        def get_unit_func(name):
            u = getattr(model.doc.data[name], 'unit', '')
            return units.hsymbols.get(u, '')
        def get_verbose_func(name):
            return getattr(model.doc.data[name], 'm_label', '')
            
        table_model_export(model._loaded, get_column_func, model, self, 
                           get_unit_func,
                           get_verbose_func)

    def show_menu(self, pt):
        self.point = pt
        QtGui.qApp.processEvents()
        self.menu.clear()
        self.menu.addAction(_('Hide'), self.hide)
        # TODO: offer checkable entries to restore hidden columns
        self.menu.addAction(_('Show more'), self.show_more)
        self.menu.addAction(_('Export'), self.export)
        self.menu.popup(self.mapToGlobal(pt))


class SummaryView(QtGui.QTableView):

    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent=None)
        self.setHorizontalHeader(SummaryHeader(parent=self))
        self.setWindowTitle(_("Data Table"))

    def set_doc(self, doc, key=False):
        m = SummaryModel()
        m.set_doc(doc)
        self.setModel(m)
        self.connect(doc, QtCore.SIGNAL('reloaded()'), self.refresh)
        self.connect(doc, QtCore.SIGNAL('updated()'), self.update)

    def refresh(self):
        logging.debug('SummaryView.refresh')
        self.model().refresh()

    def update(self):
        if self.isVisible():
            logging.debug('UPDATE SIGNAL RECEIVED')
            self.model().update()

    def showEvent(self, event):
        self.update()
        return super(SummaryView, self).showEvent(event)

    def set_idx(self, idx=-1):
        if idx < 0:
            idx = 0
        cidx = self.currentIndex()
        logging.debug('cidx', cidx)
        col = cidx.column()
        if col < 0:
            col = 0
        logging.debug('row, col', idx, col)
        midx = self.model().index(idx, col)
        self.setCurrentIndex(midx)

    def hide_show(self, col):
        pass
