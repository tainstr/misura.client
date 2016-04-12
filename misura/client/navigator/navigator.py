#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
from misura.canon.logger import Log as logging

import veusz.document as document
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
from .. import _
import quick
from .. import filedata


class StylesMenu(QtGui.QMenu):

    def __init__(self, doc, node):
        QtGui.QMenu.__init__(self, _('Styles'))
        self.doc = doc
        self.node = node
        self.addAction(_('Colorize'), self.colorize)



    

class Navigator(quick.QuickOps, QtGui.QTreeView):
    
    extension_classes = quick.domains[:]

    """List of currently opened misura Tests and reference to datasets names"""
    def __init__(self, parent=None, doc=None, mainwindow=None, context='Graphics', menu=True, status=filedata.dstats.loaded, cols=1):
        QtGui.QTreeView.__init__(self, parent)
        self.status = status
        self.ncols = cols
        self._mainwindow = mainwindow
        self.acts_status = []
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtGui.QTreeView.SelectItems)
        self.setSelectionMode(QtGui.QTreeView.ExtendedSelection)
        self.setUniformRowHeights(True)
        self.setIconSize(QtCore.QSize(24, 16))
        self.connect(self, QtCore.SIGNAL('clicked(QModelIndex)'), self.select)
        self.domains = []
        for domain in self.extension_classes:
            self.domains.append(domain(self))
        # Menu creation
        if menu:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.connect(self, QtCore.SIGNAL(
                'customContextMenuRequested(QPoint)'), self.showContextMenu)

            self.connect(self, QtCore.SIGNAL('doubleClicked(QModelIndex)'),self.double_clicked)

            ######
            # File menu
            self.file_menu = QtGui.QMenu(self)


            ######
            # Group or No-selection menu
            self.base_menu = QtGui.QMenu(self)

            self.acts_status = []
            for i, s in enumerate(filedata.dstats):
                name = filedata.dstats._fields[i]
                act = self.base_menu.addAction(
                    _(name.capitalize()), self.set_status)
                act1 = self.file_menu.addAction(act)
                act.setCheckable(True)
                if s == status:
                    act.setChecked(True)
                self.acts_status.append(act)

            self.act_del = self.base_menu.addAction(
                _('Delete'), self.deleteChildren)
            self.base_menu.addAction(_('Update view'), self.update_view)

            ######
            # Sample menu
            self.sample_menu = QtGui.QMenu(self)

            ######
            # Dataset menu
            self.dataset_menu = QtGui.QMenu(self)

            ######
            # Derived dataset menu
            self.der_menu = QtGui.QMenu(self)

            ####
            # Binary
            self.bin_menu = QtGui.QMenu(self)

        else:
            self.connect(
                self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.refresh_model)
        if doc:
            self.set_doc(doc)

    def double_clicked(self, index):
        n = self.model().data(index, role=Qt.UserRole)
        if isinstance(n, filedata.DatasetEntry) :
            self.plot(n)
        else:
            print 'Not a valid node', n


    def set_idx(self, n):
        return self.model().set_idx(n)

    def set_time(self, t):
        return self.model().set_time(t)

    def hide_show(self, *a, **k):
        return self.model().hide_show(*a, **k)

    def set_doc(self, doc):
        self.doc = doc
        self.cmd = document.CommandInterface(self.doc)
        self.setWindowTitle(_('Opened misura Tests'))
        self.mod = self.doc.model
        self.mod.ncols = self.ncols
        self.setModel(self.mod)
        # self.mod.modelReset.connect(self.restore_selection)
        self.expandAll()
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.set_status()
        self.doc.signalModified.connect(self.refresh_model)

    def update_view(self):
        self.model().refresh(True)
        self.ensure_sync_of_view_and_model()

    def refresh_model(self, ismodified=True):
        if ismodified:
            if self.model().refresh(False):
                self.ensure_sync_of_view_and_model()



    def ensure_sync_of_view_and_model(self):
        self.collapseAll()
        self.expandAll()
        self.restore_selection()

    def set_status(self):
        final = set()
        for i, s in enumerate(filedata.dstats):
            act = self.acts_status[i]
            if act.isChecked():
                final.add(s)
        if len(final) == 0:
            logging.debug('%s', 'no valid status requested')
            return
        self.status = final
        self.model().status = final
        logging.debug('%s %s', 'STATUS SET TO', final)
        self.collapseAll()
        self.expandAll()

    def select(self, idx):
        if not idx.isValid():
            return
        node = self.model().data(idx, role=Qt.UserRole)
        logging.debug('%s %s', 'select', node)
        self.emit(QtCore.SIGNAL('select()'))
        plotpath = self.model().is_plotted(node.path)
        logging.debug('%s %s %s', 'Select: plotted on', node.path, plotpath)
        if len(plotpath) == 0:
            return
        wg = self.doc.resolveFullWidgetPath(plotpath[0])
        self.mainwindow.treeedit.selectWidget(wg)
        self.emit(QtCore.SIGNAL('select(QString)'), plotpath[0])

    def restore_selection(self):
        """Restore previous selection after a model reset."""

        if(len(self.selectedIndexes()) > 0):
            self.scrollTo(self.selectedIndexes()[0])

    def update_base_menu(self, node=False):
        self.act_del.setEnabled(bool(node))

    def update_file_menu(self, node):
        self.file_menu.clear()
        self.file_menu.addAction(_('Update view'), self.refresh_model)
        for domain in self.domains:
            domain.build_file_menu(self.file_menu, node)
        
    def update_sample_menu(self, node):
        self.sample_menu.clear()
        for domain in self.domains:
            domain.build_sample_menu(self.sample_menu, node)       
        return self.sample_menu

    def update_dataset_menu(self, node):
        self.dataset_menu.clear()
        for domain in self.domains:
            domain.build_dataset_menu(self.dataset_menu, node)
        return self.dataset_menu

    def update_derived_menu(self, node):
        self.der_menu.clear()
        for domain in self.domains:
            domain.build_derived_dataset_menu(self.der_menu, node)
        return self.der_menu
    
    def update_multiary_menu(self, selection):
        self.bin_menu.clear()
        for domain in self.domains:
            domain.build_multiary_menu(self.bin_menu, selection)   

    def showContextMenu(self, pt):
        sel = self.selectedIndexes()
        n = len(sel)
        node = self.model().data(self.currentIndex(), role=Qt.UserRole)
        logging.debug('%s %s', 'showContextMenu', node)

        if node is None or not node.parent:
            self.update_base_menu()
            menu = self.base_menu
        elif n>1:
            self.update_multiary_menu(sel)
            menu = self.bin_menu 
        elif node.ds is False:
            # Identify a "summary" node
            if not node.parent.parent:
                self.update_file_menu(node)
                menu = self.file_menu
            # Identify a "sampleN" node
            elif node.name().startswith('sample'):
                menu = self.update_sample_menu(node)
            else:
                self.update_base_menu(node)
                menu = self.base_menu
        # The DatasetEntry refers to a plugin
        elif hasattr(node.ds, 'getPluginData'):
            menu = self.update_derived_menu(node)
        # The DatasetEntry refers to a standard dataset
        elif n == 1:
            menu = self.update_dataset_menu(node)
        # No active selection
        else:
            menu = self.base_menu

        # menu.popup(self.mapToGlobal(pt))
        # Synchronous call to menu, otherise selection is lost on live update
        self.model().pause(1)
        menu.exec_(self.mapToGlobal(pt))
        self.model().pause(0)
