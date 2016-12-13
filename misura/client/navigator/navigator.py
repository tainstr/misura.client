#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
import os

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
from ..filedata import operation
from veusz.dataimport.base import ImportParamsBase


class Navigator(quick.QuickOps, QtGui.QTreeView):
    previous_selection = False
    """List of currently opened misura Tests and reference to datasets names"""
    tasks = None
    convert = QtCore.pyqtSignal(str)
    converter = False
    
    def __init__(self, parent=None, doc=None, mainwindow=None, context='Graphics', menu=True, status=set([filedata.dstats.loaded]), cols=1):
        QtGui.QTreeView.__init__(self, parent)
        self.status = status
        self.ncols = cols
        self._mainwindow = mainwindow
        self.acts_status = []
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
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
            self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), 
                         self.showContextMenu)

            self.connect(self, QtCore.SIGNAL('doubleClicked(QModelIndex)'),
                         self.double_clicked)
            
            #TODO: all these should be implicit
            self.base_menu = QtGui.QMenu(self)
            self.add_status_actions(self.base_menu)
            self.file_menu = QtGui.QMenu(_('File'), self)
            self.group_menu = QtGui.QMenu(_('Node'), self)
            self.sample_menu = QtGui.QMenu(_('Sample'), self)
            self.dataset_menu = QtGui.QMenu(_('Dataset'), self)
            self.der_menu = QtGui.QMenu(_('Derived'), self)
            self.multi_menu = QtGui.QMenu(_('Multiary'), self)

        else:
            self.connect(
                self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.refresh_model)
        if doc:
            self.set_doc(doc)
            
        self.connect(self, QtCore.SIGNAL(
            'do_open(QString)'), self.open_file)
        self.convert.connect(self.convert_file)
        
        self.create_shortcuts()
        
    def create_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_F), 
                        self, 
                        self.edit_regex_rule)
        
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_F5), 
                        self, 
                        self.update_view)

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
        
        if hasattr(self.mainwindow.plot,'set_navigator'):
            self.mainwindow.plot.set_navigator(self)
            
    def open_file(self, path, **kw):
        logging.info('OPEN FILE', path)
        self.doc.proxy = False
        op = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=path, gen_rule_load=True)
        )
        self.doc.applyOperation(op)
        confdb.mem_file(path, op.measurename)
        # Load additional curves for plotting
        plugin_class, plot_rule_func = filedata.get_default_plot_plugin_class(op.instrument)
        plot_rule = plot_rule_func(confdb, op.proxy.conf)
        #op = filedata.OperationMisuraImport.from_rule(plot_rule, path)
        #self.doc.applyOperation(op)
        # Default plot
        #TODO: handle default plot opening
        p = plugin_class()
        logging.debug('Default plot on imported names', op.imported_names)
        result = p.apply(self._mainwindow.cmd, {'dsn': op.imported_names, 
                                       'rule': plot_rule})
        return op
        
    def convert_file(self, path):
        logging.info('CONVERT FILE', path)
        filedata.convert_file(self, path)
        
    def _open_converted(self):
        params = ImportParamsBase(filename=self.converter.outpath)
        LF = operation.get_linked(self.doc, params, create=False)
        if not LF:
            op = self.open_file(self.converter.outpath)
            LF = op.LF
        self.converter.post_open_file(self, prefix=LF.prefix)
        
    def _failed_conversion(self, error):
        QtGui.QMessageBox.warning(self, _("Failed conversion"), error)
    


    def set_idx(self, n):
        return self.model().set_idx(n)

    def set_time(self, t):
        return self.model().set_time(t)

    def dragEnterEvent(self, event):
        logging.debug('dragEnterEvent', event.mimeData())
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
                        
    def dragMoveEvent(self, event):
        logging.debug('dragMoveEvent', event.mimeData())
        if event.mimeData().hasUrls():
            event.acceptProposedAction()        

    def dropEvent(self, drop_event):
        urls = drop_event.mimeData().urls()
        logging.debug('dropEvent', urls)
        drop_event.accept()
        for url in urls:
            url = url.toString().replace('file://', '')
            # on windows, remove also the first "/"
            if os.name.lower() == 'nt':
                url = url[1:]
            self.convert.emit(url)

    def hide_show(self, *a, **k):
        return self.model().hide_show(*a, **k)
    
    def get_page(self):
        n = self.mainwindow.plot.getPageNumber()
        page = self.doc.basewidget.getPage(n)
        return page

    def update_view(self):
        if len(self.doc.suspendupdates)>0:
            logging.debug('Cannot update_view: suspendedupdates!')
            return
        if not self.previous_selection:
            self.previous_selection = self.current_node_path
        page = self.get_page()
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
        if len(jdx) > 0:
            self.setExpanded(jdx[-1], True)
            if select:
                # Select also
                self.selectionModel().setCurrentIndex(jdx[-1], QtGui.QItemSelectionModel.Select)
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
        
    def domain_double_clicked(self, node):
        """Execute double_clicked action on each domain"""
        for domain in self.domains:
            r = domain.double_clicked(node)
            if r:
                logging.debug('double_clicked', node.path, domain)
                self.restore_selection()
                return True
        return False        

    def double_clicked(self, index):
        self.sync_currentwidget(update_navigator_selection=False)
        node = self.model().data(index, role=Qt.UserRole)
        self.previous_selection = node.path
        if isinstance(node, filedata.DatasetEntry):
            done = self.plot(node)
        else:
            done = self.domain_double_clicked(node)
        self.restore_selection()
        if not done:
            logging.error('Not a valid node', node)
        return done

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
        act = menu.addAction(_('Set filter (CTRL+F)'), self.edit_regex_rule)
        self.acts_status.append(act)
        self.act_del = menu.addAction(_('Delete'), self.deleteChildren)
        self.acts_status.append(self.act_del)
        act = menu.addAction(_('Update view (F5)'), self.update_view)
        self.acts_status.append(act)
        return True
    
    
    def edit_regex_rule(self, node=False):
        #TODO: bring here all filtering options
        root = self.model().tree
        out, status = QtGui.QInputDialog.getText(self, _('Edit Navigator RegEx'), 
                                   _('Enter a regular expression'), 
                                   text=root.regex_rule)
        if not status:
            return False
        root.set_filter(str(out))
        if not self.model().paused:
            self.update_view()
        

    def update_base_menu(self, node=False, base_menu=False):
        base_menu.clear()
        for domain in self.domains:
            domain.build_base_menu(base_menu, node)
        self.add_status_actions(base_menu)
        self.act_del.setEnabled(bool(node))
        return base_menu

    def update_group_menu(self, node, group_menu):
        group_menu.clear()
        for domain in self.domains:
            domain.build_group_menu(group_menu, node)
        self.add_status_actions(group_menu)
        self.act_del.setEnabled(bool(node))
        return group_menu

    def update_file_menu(self, node, file_menu):
        file_menu.clear()
        file_menu.addAction(_('Update view'), self.update_view)
        for domain in self.domains:
            domain.build_file_menu(file_menu, node)
        self.add_status_actions(file_menu)
        self.act_del.setEnabled(bool(node))
        return file_menu

    def update_sample_menu(self, node, sample_menu):
        sample_menu.clear()
        for domain in self.domains:
            domain.build_sample_menu(sample_menu, node)
        return sample_menu

    def update_dataset_menu(self, node, dataset_menu):
        dataset_menu.clear()
        for domain in self.domains:
            domain.build_dataset_menu(dataset_menu, node)
        return dataset_menu

    def update_derived_menu(self, node, der_menu):
        der_menu.clear()
        for domain in self.domains:
            domain.build_derived_dataset_menu(der_menu, node)
        return der_menu

    def update_multiary_menu(self, selection, multi_menu):
        multi_menu.clear()
        for domain in self.domains:
            domain.build_multiary_menu(multi_menu, selection)
        return multi_menu
    
    def sync_currentwidget(self, *foo, **kw):
        selected = self.mainwindow.plot.lastwidgetsselected
        logging.debug('SELECTED widgets', [el.path for el in selected])
        tn = [wg.typename for wg in selected]
        if len(selected):
            i = 0
            if 'xy' in tn:
                i = tn.index('xy')
            self.cmd.currentwidget = selected[i]
        else:
            self.cmd.currentwidget = self.get_page()
        up = kw.get('update_navigator_selection', True)
        if self.cmd.currentwidget.typename =='xy' and up:
            dsn = self.cmd.currentwidget.settings.yData
            node = self.model().tree.traverse(dsn)
            self.selectionModel().clear()
            self.expand_node_path(node, select=True)
        return self.cmd.currentwidget
    
    def buildContextMenu(self, node, sel=[], menu=False):
        n = len(sel)
        if node is None or not node.parent:
            menu = self.update_base_menu(node, menu or self.base_menu)
        elif n>1:
            menu = self.update_multiary_menu(sel, menu or self.multi_menu)
        elif node.ds is False:
            # Identify a "summary" node
            if not node.parent.parent:
                menu = self.update_file_menu(node, menu or self.file_menu)
            # Identify a "sampleN" node
            elif node.name().startswith('sample'):
                menu = self.update_sample_menu(node, menu or self.sample_menu)
            else:
                menu = self.update_group_menu(node, menu or self.group_menu)
        # The DatasetEntry refers to a plugin
        elif hasattr(node.ds, 'getPluginData'):
            menu = self.update_derived_menu(node, menu or self.der_menu)
        # The DatasetEntry refers to a standard dataset
        elif n <= 1:
            menu = self.update_dataset_menu(node, menu or self.dataset_menu)
        # No active selection
        else:
            menu = self.update_base_menu(node, menu or self.base_menu)
        return menu


    def showContextMenu(self, pt):
        # Refresh currentwidget in cmd interface
        self.sync_currentwidget(update_navigator_selection=False)
        self.previous_selection = self.current_node_path
        sel = self.selectedIndexes()
        node = self.model().data(self.currentIndex(), role=Qt.UserRole)
        logging.debug('%s %s', 'showContextMenu', node)
        menu = self.buildContextMenu(node, sel)
        
        # menu.popup(self.mapToGlobal(pt))
        # Synchronous call to menu, otherise selection is lost on live update
        self.model().pause(1)
        menu.exec_(self.mapToGlobal(pt))
        self.model().pause(0)
        self.update_view()
