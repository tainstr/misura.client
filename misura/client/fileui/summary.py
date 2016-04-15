#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tabular view of data in a MisuraDocument"""
import os
from misura.canon.logger import Log as logging

from .. import iutils, _
import re
from misura.client.clientconf import settings
# TODO: these functions should be generalized and applied also by the
# navigator. THey should also present data in hierarchy (not plain).
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
voididx = QtCore.QModelIndex()


class SummaryModel(QtCore.QAbstractTableModel):
    _rowCount = 0
    _loaded = []

    def __init__(self, *a, **k):
        QtCore.QAbstractTableModel.__init__(self, *a, **k)
        self.auto_load = True

    def set_doc(self, doc):
        self.doc = doc
        self._loaded = []
        self._rowCount = 0
        self.update()

    def set_loaded(self, loaded):
        if set(loaded) != set(self._loaded):
            self._loaded = loaded
            self.emit(QtCore.SIGNAL('headerDataChanged(int,int,int)'),
                      QtCore.Qt.Horizontal, 0, len(loaded))
            return True
        return False

    @property
    def model(self):
        return self.doc.model

    @property
    def tree(self):
        return self.model.tree

    def refresh(self):
        self.model.refresh()
        self.update()

    def update(self):
        r = False
        # New rows length
        start = self._rowCount
        end = len(self.doc.data.get('0:t', []))
        # New header (lists all loaded columns/non-zero)
        if self.auto_load:
            ldd = []
            for k, ds in self.doc.data.iteritems():
                if len(ds) > 0:
                    ldd.append(k)
            r = self.set_loaded(ldd)
        # Update length
        if start != end:
            self.emit(QtCore.SIGNAL('rowsInserted(QModelIndex,int,int)'),
                      self.index(0, 0), start, end)
            r = True
        if r:
            self.emit(QtCore.SIGNAL('modelReset()'))
        return r

    def columnCount(self, parent):
        return len(self._loaded)

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
        if not self.doc.data.has_key(self._loaded[0]):
            return 0
        self._rowCount = len(self.doc.data[self._loaded[0]].data)
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

    def export(self, path='/tmp/misura/m.csv', order=False, sep=';\t', header=False):
        """Export to csv file `path`, following column order `order`, using separator `sep`,
        prepending `header`"""
        # Terrible way of reordering!
        if order is not False:
            ordered = [None] * len(self._loaded)
            for i, j in order.iteritems():
                ordered[j] = self._loaded[i]
            for i in range(ordered.count(None)):
                ordered.remove(None)
        else:
            ordered = self._loaded[:]
        logging.debug('%s %s', 'ordered', ordered)
        n = len(ordered)
        if not n:
            logging.debug('%s', 'No columns to export.')
            return False
        f = open(path, 'w')
        if header:
            f.write(header + '\n')
        msg = ('{}' + sep) * len(ordered) + '\n'
        ch = [h.replace('summary/', '') for h in ordered]
        f.write(msg.format(*ch))
        dat = []
        nmax = 0
        for h in ordered:
            d = self.doc.data[h].data
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
        logging.debug('%s %s', 'Hide', i)

    def show_more(self):
        """Load more columns from document model"""
        # TODO: load a treeview with checkable items in order to load more
        pass

    def export(self):
        """Export to CSV file"""
        # TODO: produce a header section based on present samples' metadata
        d = settings.value('/FileSaveToDir', os.path.expanduser('~'))
        path = os.path.join(str(d), 'export.csv')
        dest = str(QtGui.QFileDialog.getSaveFileName(
            self, "Export To CSV...", path))
        if dest == '':
            return
        if not dest.lower().endswith('.csv'):
            dest += '.csv'
        # Compute visual index order mapping to logical index,
        # as a consequence of visually moving columns
        order = {}
        for i in range(self.parent().model().columnCount(self.currentIndex())):
            if self.isSectionHidden(i):
                continue
            order[i] = self.visualIndex(i)
        self.parent().model().export(path=dest, order=order)

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
        self.model().refresh()

    def update(self):
        self.model().update()

    def showEvent(self, event):
        self.update()
        return super(SummaryView, self).showEvent(event)

    def set_idx(self, idx=-1):
        if idx < 0:
            idx = 0
        cidx = self.currentIndex()
        logging.debug('%s %s', 'cidx', cidx)
        col = cidx.column()
        if col < 0:
            col = 0
        logging.debug('%s %s %s %s', 'row, col', idx, col)
        midx = self.model().index(idx, col)
        self.setCurrentIndex(midx)

    def hide_show(self, col):
        pass
