#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
from misura.canon.logger import Log as logging
from misura.canon.plugin import navigator_domains
from misura.canon.plugin.domains import node, nodes
import veusz.document as document
import veusz.plugins
import veusz.dialogs
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
from .. import _
import quick
from .. import filedata
from .. import live
from .. import plugin
from ..clientconf import confdb

class Navigator(quick.QuickOps, QtGui.QTreeView):
    previous_selection = False
    """List of currently opened misura Tests and reference to datasets names"""
    tasks = None
    def __init__(self, parent=None, doc=None, mainwindow=None, context='Graphics', menu=True, status=set([filedata.dstats.loaded]), cols=1):
        QtGui.QTreeView.__init__(self, parent)
        self.status = status
        self.ncols = cols
        self._mainwindow = mainwindow
        self.acts_status = []
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setAlternatingRowColors(True)
        self.setExpandsOnDoubleClick(False)
        self.setSelectionBehavior(QtGui.QTreeView.SelectItems)
        self.setSelectionMode(QtGui.QTreeView.ExtendedSelection)
        self.setUniformRowHeights(True)
        self.setIconSize(QtCore.QSize(24, 16))
        self.connect(self, QtCore.SIGNAL('clicked(QModelIndex)'), self.select)
        self.connect(self, QtCore.SIGNAL('updateView()'), self.update_view, QtCore.Qt.QueuedConnection)
        self.domains = []
        done = set([])
        for domain in navigator_domains:
            if domain in done:
                continue
            self.domains.append(domain(self))
            done.add(domain)
        # Menu creation
        if menu:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.connect(self, QtCore.SIGNAL(
                'customContextMenuRequested(QPoint)'), self.showContextMenu)

            self.connect(self, QtCore.SIGNAL('doubleClicked(QModelIndex)'),self.double_clicked)
            self.base_menu = QtGui.QMenu(self)
            self.add_status_actions(self.base_menu)
            self.file_menu = QtGui.QMenu(self)
            self.group_menu = QtGui.QMenu(self)
            self.sample_menu = QtGui.QMenu(self)
            self.dataset_menu = QtGui.QMenu(self)
            self.der_menu = QtGui.QMenu(self)
            self.multi_menu = QtGui.QMenu(self)

        else:
            self.connect(
                self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.refresh_model)
        if doc:
            self.set_doc(doc)
        
    @property
    def tasks(self):
        return live.registry.tasks

    def selectedIndexesPublic(self, *a, **k):
        return self.selectedIndexes()

    def set_doc(self, doc):
        self.previous_selection = False
        self.doc = doc
        self.cmd = document.CommandInterface(self.doc)
        self.setWindowTitle(_('Opened Misura Tests'))
        self.mod = self.doc.model
        self.mod.ncols = self.ncols
        self.setModel(self.mod)
        self.expandAll()
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.set_status()
        self.doc.signalModified.connect(self.refresh_model)
        self.mod.sigPageChanged.connect(self.ensure_sync_of_view_and_model)
        if self.ncols>1:
            self.setColumnWidth(0, 400)


    def set_idx(self, n):
        return self.model().set_idx(n)

    def set_time(self, t):
        return self.model().set_time(t)

    def hide_show(self, *a, **k):
        return self.model().hide_show(*a, **k)

    def update_view(self):
        if len(self.doc.suspendupdates)>0:
            return
        if not self.previous_selection:
            self.previous_selection = self.current_node_path
        n = self.mainwindow.plot.getPageNumber()
        page = self.doc.basewidget.getPage(n)
        self.model().set_page(page.path)
        self.model().refresh(True)
        self.ensure_sync_of_view_and_model()

    def refresh_model(self, ismodified=True):
        if not self.previous_selection:
            self.previous_selection = self.current_node_path
        if ismodified:
            if self.model().refresh(False):
                self.ensure_sync_of_view_and_model()
        if self.doc.auto_changeset+2!=self.doc.changeset:
            self.ensure_sync_of_view_and_model()

    def ensure_sync_of_view_and_model(self):
        self.collapseAll()
        self.restore_selection()

    @property
    def current_node_path(self):
        node = self.model().data(self.currentIndex(), role=QtCore.Qt.UserRole)
        if node:
            return node.path
        return False

    def expand_node_path(self, node, select=False):
        jdx = self.model().index_path(node)
        self.setExpanded(jdx[-1], True)
        if select:
            # Select also
            self.selectionModel().setCurrentIndex(
                    jdx[-1], QtGui.QItemSelectionModel.Select)
        # Qt bug: without scrollTo, expansion is not effective!!!
        self.scrollTo(jdx[-1])
        return jdx

    def expand_plotted_nodes(self):
        for node in self.model().list_plotted():
            if node:
                self.expand_node_path(node, select=False)

    def restore_selection(self):
        """Restore previous selection after a model reset."""
        self.expand_plotted_nodes()

        if not self.previous_selection:
            return

        node = self.model().tree.traverse(self.previous_selection)
        self.previous_selection = False
        if not node:
            return
        self.expand_node_path(node, select=True)



    def set_status(self):
        self.previous_selection = self.current_node_path
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
        self.ensure_sync_of_view_and_model()

    def select(self, idx):
        if not idx.isValid():
            return
        node = self.model().data(idx, role=Qt.UserRole)
        self.emit(QtCore.SIGNAL('select()'))
        plotpath = self.model().is_plotted(node.path)
        self.previous_selection = node.path
        logging.debug('Select: plotted on', node.path, plotpath)
        if len(plotpath) == 0:
            return
        wg = self.doc.resolveFullWidgetPath(plotpath[0])
        self.mainwindow.treeedit.selectWidget(wg)
        self.emit(QtCore.SIGNAL('select(QString)'), plotpath[0])

    def double_clicked(self, index):
        node = self.model().data(index, role=Qt.UserRole)
        self.previous_selection = node.path
        for domain in self.domains:
            r = domain.double_clicked(node)
            if r:
                logging.debug('double_clicked', node.path, domain)
                self.restore_selection()
                return True

        if isinstance(node, filedata.DatasetEntry) :
            self.plot(node)
        else:
            logging.error('Not a valid node', node)
            self.restore_selection()
            return False
        self.restore_selection()
        return True

    def add_status_actions(self, menu):
        menu.addSeparator()
        self.acts_status = []
        for i, s in enumerate(filedata.dstats):
            name = filedata.dstats._fields[i]
            act = menu.addAction(
                _(name.capitalize()), self.set_status)
            act.setCheckable(True)
            if s in self.status:
                print 'set action as checked', name, s, self.status
                act.setChecked(True)
            else:
                print 'set action as unchecked', name, s, self.status
            self.acts_status.append(act)

        self.act_del = menu.addAction(_('Delete'), self.deleteChildren)
        self.acts_status.append(self.act_del)
        act = menu.addAction(_('Update view'), self.update_view)
        self.acts_status.append(act)
        return True

    def update_base_menu(self, node=False):
        self.base_menu.clear()
        for domain in self.domains:
            domain.build_base_menu(self.base_menu, node)
        self.add_status_actions(self.base_menu)
        self.act_del.setEnabled(bool(node))
        return self.base_menu

    def update_group_menu(self, node=False):
        self.group_menu.clear()
        for domain in self.domains:
            domain.build_group_menu(self.group_menu, node)
        self.add_status_actions(self.group_menu)
        self.act_del.setEnabled(bool(node))
        return self.group_menu

    def update_file_menu(self, node):
        self.file_menu.clear()
        self.file_menu.addAction(_('Update view'), self.refresh_model)
        for domain in self.domains:
            domain.build_file_menu(self.file_menu, node)
        self.add_status_actions(self.file_menu)
        self.act_del.setEnabled(bool(node))
        return self.file_menu

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
        self.multi_menu.clear()
        for domain in self.domains:
            domain.build_multiary_menu(self.multi_menu, selection)
        return self.multi_menu

    def showContextMenu(self, pt):
        self.previous_selection = self.current_node_path
        sel = self.selectedIndexes()
        n = len(sel)
        node = self.model().data(self.currentIndex(), role=Qt.UserRole)
        logging.debug('%s %s', 'showContextMenu', node)

        if node is None or not node.parent:
            menu = self.update_base_menu()
        elif n>1:
            menu = self.update_multiary_menu(sel)
        elif node.ds is False:
            # Identify a "summary" node
            if not node.parent.parent:
                menu = self.update_file_menu(node)
            # Identify a "sampleN" node
            elif node.name().startswith('sample'):
                menu = self.update_sample_menu(node)
            else:
                menu = self.update_group_menu(node)
        # The DatasetEntry refers to a plugin
        elif hasattr(node.ds, 'getPluginData'):
            menu = self.update_derived_menu(node)
        # The DatasetEntry refers to a standard dataset
        elif n == 1:
            menu = self.update_dataset_menu(node)
        # No active selection
        else:
            menu = self.update_base_menu(node)

        # menu.popup(self.mapToGlobal(pt))
        # Synchronous call to menu, otherise selection is lost on live update
        self.model().pause(1)
        menu.exec_(self.mapToGlobal(pt))
        self.model().pause(0)
        self.update_view()
