#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
import os
import re
import functools
from misura.canon.logger import get_module_logging
from misura.client.filedata.operation import getUsedPrefixes
logging = get_module_logging(__name__)
from misura.canon.plugin import navigator_domains
from misura.canon.plugin.domains import node
from misura.canon.option import match_node_path
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
from .. import iutils
from ..filedata import operation
from veusz.dataimport.base import ImportParamsBase

style = """QTreeView {
    show-decoration-selected: 1;
}

QTreeView::item {
     border: 1px solid #d9d9d9;
    border-top-color: transparent;
    border-bottom-color: transparent;
}

QTreeView::item:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #e7effd, stop: 1 #cbdaf1);
    border: 1px solid #bfcde4;
}

QTreeView::item:selected {
    border: 1px solid #567dbc;
}

QTreeView::item:selected:active{
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6ea1f1, stop: 1 #567dbc);
}

QTreeView::item:selected:!active {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6b9be8, stop: 1 #577fbf);
}"""

class NavigatorToolbar(QtGui.QToolBar):
    versionChanged = QtCore.pyqtSignal(str)
    versionRemoved = QtCore.pyqtSignal(str, str)
    plotChanged = QtCore.pyqtSignal(str, str)
    versionSaved = QtCore.pyqtSignal(str)
    plotSaved = QtCore.pyqtSignal(str)
    
    def __init__(self, navigator, parent=None):
        super(NavigatorToolbar, self).__init__(parent=parent)
        self.navigator = navigator
        self.navigator.selectionModel().currentChanged.connect(self.update_navtoolbar)
        
    def addMenu(self, name_or_menu):
        if isinstance(name_or_menu, basestring):
            name = name_or_menu
            menu = QtGui.QMenu(name)
        else:
            menu = name_or_menu
            name = menu.title()
        return menu
    
    def save(self):
        return self.save_menu.save_version()
    
    def add_save_menu(self):
        if not self.actions():
            return False
        dom = self.navigator.domainsMap['DataNavigatorDomain']
        sm = dom.add_versions_menu()
        if not sm:
            logging.debug('Cannot add_versions_menu')
            return False
        self.save_menu = sm
        self.act_save = QtGui.QAction(iutils.theme_icon('media-floppy'), _('Save in Misura file'), self)
        self.act_save.triggered.connect(self.save)
        self.act_save.setMenu(self.save_menu)
        self.insertAction(self.actions()[0], self.act_save)
        self.save_menu.versionSaved.connect(self.versionSaved.emit)
        self.save_menu.plotSaved.connect(self.plotSaved.emit)
        self.save_menu.versionChanged.connect(self.versionChanged.emit)
        self.save_menu.versionRemoved.connect(self.versionRemoved.emit)
        self.save_menu.plotChanged.connect(self.plotChanged.emit)
        return True
        
    def update_navtoolbar(self, *foo):
        self.clear()
        self.navigator.buildContextMenu(menu=self, 
                                        tree_actions=self.navigator.isVisible())
        for a in self.actions():          
            if a.icon().isNull():
                self.removeAction(a)
        self.add_save_menu()
        

class Navigator(quick.QuickOps, QtGui.QTreeView):
    previous_selection = False
    """List of currently opened misura Tests and reference to datasets names"""
    tasks = None
    convert = QtCore.pyqtSignal(str)
    converter = False
    doc = False
    hovered = False
    
    def __init__(self, parent=None, doc=None, mainwindow=None, context='Graphics', menu=True, status=set([filedata.dstats.loaded]), cols=1):
        QtGui.QTreeView.__init__(self, parent)
        self.setStyleSheet(style)
        self.widgets_registry = {}
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
        self.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.setIconSize(QtCore.QSize(24, 16))
        self.connect(self, QtCore.SIGNAL('clicked(QModelIndex)'), self.select)
        self.connect(self, QtCore.SIGNAL('updateView()'), self.update_view, QtCore.Qt.QueuedConnection)
        self.domains = []
        self.domainsMap = {}
        for domain in navigator_domains:
            if domain.__name__ in self.domainsMap:
                continue
            dom = domain(self)
            self.domains.append(dom)
            self.domainsMap[domain.__name__] = dom
        # Menu creation
        if menu:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), 
                         self.showContextMenu)

            self.connect(self, QtCore.SIGNAL('doubleClicked(QModelIndex)'),
                         self.double_clicked)
            
            #TODO: all these should be implicit
            self.base_menu = QtGui.QMenu(self)
            self.add_tree_actions(self.base_menu)
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
        
    @property
    def appwindow(self):
        found = False
        p = self.parent()
        while p:
            if hasattr(p, 'area'):
                found = True
                break
            p = p.parent()
        if found:
            return p
        return False
    
    def match_node_path(self, node, rule):
        return match_node_path(node, rule)
    
    def show_widget_key(self, key):
        """Shows existing widgets or subwindows by key"""
        wg = self.widgets_registry.get(key, False)
        if not wg:
            return False
        p = self.appwindow
        if p:
            if wg in p.centralWidget().subWindowList():
                wg.showNormal()
            else:
                # Was closed!
                self.widgets_registry.pop(key)
                return False
        # Spare window
        wg.show()
        return wg
        
    def show_widget(self, wg, key=False, width=False, height=False):
        """Show widget `wg` as new mdi window, if possible, else as separate new window."""
        p = self.appwindow
        key = key or id(wg)
        if not p:
            wg.show()
            self.widgets_registry[key] = wg
            return wg
        win = p.centralWidget().addSubWindow(wg)
        win.setWindowTitle(wg.windowTitle())
        w = width or win.width()
        h = height or win.height()
        win.resize(w, h)
        win.showNormal()
        self.widgets_registry[key] = win
        
        return win
        
    def create_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_F), 
                        self, 
                        self.edit_regex_rule,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)
        
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_F5), 
                        self, 
                        self.update_view,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)

        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_C), 
                        self, 
                        self.collapse_siblings,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)
        
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_E), 
                        self, 
                        self.expandAll,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)
        
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT +QtCore.Qt.Key_E), 
                        self, 
                        self.expand_plotted_nodes,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)

    @property
    def tasks(self):
        return live.registry.tasks

    def selectedIndexesPublic(self, *a, **k):
        return self.selectedIndexes()

    def set_doc(self, doc):
        self.previous_selection = False, False
        self.doc = doc
        self.cmd = document.CommandInterface(self.doc)
        self.setWindowTitle(_('Opened Misura Tests'))
        self.mod = self.doc.model
        self.mod.ncols = self.ncols
        self.setModel(self.mod)
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.set_status()
        self.expandAll()
        self.doc.signalModified.connect(self.refresh_model)
        self.doc.sigConfProxyModified.connect(self.update_view)
        self.mod.sigPageChanged.connect(self.ensure_sync_of_view_and_model)
        self.mod.modelReset.connect(self.ensure_sync_of_view_and_model)
        if self.ncols>1:
            self.setColumnWidth(0, 400)
        
        if hasattr(self.mainwindow.plot,'set_navigator'):
            self.mainwindow.plot.set_navigator(self)
            
        self.doc.sig_save_started.connect(functools.partial(self.pause, 1))
        self.doc.sig_save_done.connect(functools.partial(self.pause, 0))
            
    def open_file(self, path, **kw):
        self.pause(True)
        logging.info('OPEN FILE', path)
        #self.doc.proxy = False
        op = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=path, gen_rule_load=True)
        )
        self.doc.applyOperation(op)
        confdb.mem_file(path, op.measurename)
        # Load additional curves for plotting
        plugin_class, plot_rule_func = filedata.get_default_plot_plugin_class(op.instrument)
        plot_rule = plot_rule_func(confdb, op.proxy.conf)
        p = plugin_class()
        #dsn = op.imported_names
        dsn = self.doc.data.keys()
        logging.debug('Default plot on imported names', repr(plot_rule), op.imported_names)
        result = p.apply(self._mainwindow.cmd, {'dsn': dsn, 
                                       'rule': plot_rule})
        self.pause(False)
        self.refresh_model()
        return op
    
    def reset_document(self):
        """Wipe the current document, reopen each previously contained file and 
        create default plots accordingly"""
        files = getUsedPrefixes(self.doc).keys()
        op = document.OperationToolsPlugin(plugin.MakeDefaultDoc(), {'keep_data':True})
        self.doc.applyOperation(op)
        logging.debug('reset_document: wiped')
        for filename in files:
            logging.debug('reset_document', filename)
            self.open_file(filename)
        
        # Autoresize if in browser
        getattr(self.mainwindow.plot.parent(), 'fitSize', 
                lambda *a: 1)()
        
        
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
        logging.debug('update_view')
        if len(self.doc.suspendupdates)>0:
            logging.debug('Cannot update_view: suspendedupdates!')
            return
        #if not self.previous_selection:
        self.previous_selection = self.current_node_path
        page = self.get_page()
        if page:
            self.model().set_page(page.path)
        self.model().refresh(True)

    def refresh_model(self, ismodified=True):
        if not self.previous_selection:
            self.previous_selection = self.current_node_path
        if ismodified:
            if self.model().refresh(False):
                self.ensure_sync_of_view_and_model()
                return True
        #if self.doc.auto_changeset+2!=self.doc.changeset:
        #    self.ensure_sync_of_view_and_model()
        #    return True
        return False

    def ensure_sync_of_view_and_model(self, *foo):
        logging.debug('ensure_sync_of_view_and_model')
        self.restore_selection()

    @property
    def current_node_path(self):
        node = self.model().data(self.currentIndex(), role=QtCore.Qt.UserRole)
        if node:
            return node.path, self.visualRect(self.currentIndex())
        return False, False
    
    def expand_node_path(self, node, select=False):
        jdx = self.model().index_path(node)
        if len(jdx) == 0:
            logging.debug('expand_node_path: empty')
            return jdx
        self.setExpanded(jdx[-1], True)
        if select==2:
            self.selectionModel().clear()
        if select:
            # Select also
            self.selectionModel().setCurrentIndex(jdx[-1], QtGui.QItemSelectionModel.Select)
        # Qt bug: without scrollTo, expansion is not effective!!!
        self.scrollTo(jdx[-1])
        return jdx

    def expand_plotted_nodes(self):
        logging.debug('expand_plotted_nodes')
        self.collapseAll()
        for node in self.model().list_plotted():
            if node:
                self.expand_node_path(node, select=False)

    def restore_selection(self):
        """Restore previous selection after a model reset."""
        self.expand_plotted_nodes()
        logging.debug('restore_selection', self.previous_selection)
        if not self.previous_selection[0]:
            return

        node = self.model().tree.traverse(self.previous_selection[0])
        
        if not node:
            self.previous_selection = False, False
            return
        logging.debug('EXPANDING previous_selection', node.path, self.previous_selection)
        self.expand_node_path(node, select=True)
        # Restore visual position
        rect0 = self.previous_selection[1]
        rect1 = self.visualRect(self.model().indexFromNode(node))
        delta = rect1.y()-rect0.y()
        b = self.verticalScrollBar()
        v1 = min(b.value()+delta, b.maximum())
        v2 = max(v1, b.minimum())
        b.setValue(v2)
        rect1 = self.visualRect(self.model().indexFromNode(node))
        self.previous_selection = self.previous_selection[0], rect1

    def set_status(self):
        self.previous_selection = self.current_node_path
        final = set()
        for i, s in enumerate(filedata.dstats):
            act = self.acts_status[i]
            if act.isChecked():
                final.add(s)
        if len(final) == 0:
            logging.debug('no valid status requested')
            final = self.status
        self.status = final
        self.model().status = final
        logging.debug('STATUS SET TO', final)
        self.ensure_sync_of_view_and_model()

    def select(self, idx):
        if not idx.isValid():
            return
        node = self.model().data(idx, role=Qt.UserRole)
        self.emit(QtCore.SIGNAL('select()'))
        plotpath = self.model().is_plotted(node.path)
        self.previous_selection = self.current_node_path
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
                return True
        return False        

    def double_clicked(self, index):
        self.sync_currentwidget(update_navigator_selection=False)
        node = self.model().data(index, role=Qt.UserRole)
        self.previous_selection = self.current_node_path
        if isinstance(node, filedata.DatasetEntry):
            done = self.plot(node)
        else:
            done = self.domain_double_clicked(node)
        self.restore_selection()
        if not done:
            logging.error('Not a valid node', node)
        return done

    def add_tree_actions(self, menu, node=False):
        menu.addSeparator()
        menu.addAction(iutils.theme_icon('nav_expand'), _('Expand all (E)'), self.expandAll)
        menu.addAction(iutils.theme_icon('nav_collapse'), _('Collapse siblings (C)'), self.collapse_siblings)
        menu.addAction(iutils.theme_icon('nav_expand_plotted'), _('Expand plotted (Alt+E)'), self.expand_plotted_nodes)
        self.acts_status = []
        for i, s in enumerate(filedata.dstats):
            name = filedata.dstats._fields[i]
            act = menu.addAction(iutils.theme_icon('nav_'+name.capitalize()),
                _(name.capitalize()), self.set_status)
            act.setCheckable(True)
            if s in self.status:
                act.setChecked(True)
            self.acts_status.append(act)
        act = menu.addAction(iutils.theme_icon('nav_filter'),_('Set filter (CTRL+F)'), self.edit_regex_rule)
        self.acts_status.append(act)
        if not node:
            self.act_del = menu.addAction(_('Delete'), self.deleteChildren)
        self.acts_status.append(self.act_del)
        act = menu.addAction(_('Update view (F5)'), self.update_view)
        self.acts_status.append(act)
        return True
    
    def add_reset_plot_action(self, menu):
        menu.addSeparator()
        menu.addAction(iutils.theme_icon('document-new'), 
                       _('Reset plot'), 
                       self.reset_document)
        return True
        
    
    @node
    def collapse_siblings(self, node=False):
        if not node:
            logging.debug('No node selected for collapse')
            return False
        if not node.parent:
            logging.debug('Collapsing all')
            self.collapseAll()
            return False
        
        # Find the node level
        level = self.model().index_path(node)
        root = self.model().indexFromNode(node.root)
        level = len(level)
        
        siblings = [root]
        # Collect all indexes at the same level as node
        for lev in range(level):
            for i,idx in enumerate(siblings[:]):
                if i==0:
                    siblings = []
                siblings += self.model().list_children(idx)
            
        for idx in siblings:
            self.collapse(idx)
        
    
    
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
        

    def update_base_menu(self, node=False, base_menu=False, tree_actions=False):
        base_menu.clear()
        for domain in self.domains:
            domain.build_base_menu(base_menu, node)
        if tree_actions:
            self.add_tree_actions(base_menu)
            self.act_del.setEnabled(bool(node))
        return base_menu

    def update_group_menu(self, node, group_menu, tree_actions=False):
        group_menu.clear()
        for domain in self.domains:
            domain.build_group_menu(group_menu, node)
        if tree_actions:
            self.add_tree_actions(group_menu)
            self.act_del.setEnabled(bool(node))
        return group_menu

    def update_file_menu(self, node, file_menu, tree_actions=False):
        file_menu.clear()
        file_menu.addAction(_('Update view'), self.update_view)
        for domain in self.domains:
            domain.build_file_menu(file_menu, node)
        if tree_actions:
            self.add_tree_actions(file_menu, node)
            self.act_del.setEnabled(bool(node))
        return file_menu

    def update_sample_menu(self, node, sample_menu, tree_actions=False):
        sample_menu.clear()
        for domain in self.domains:
            domain.build_sample_menu(sample_menu, node)
        if tree_actions:
            self.add_tree_actions(sample_menu)
            self.act_del.setEnabled(bool(node))
        return sample_menu

    def update_dataset_menu(self, node, dataset_menu, tree_actions=False):
        dataset_menu.clear()
        for domain in self.domains:
            domain.build_dataset_menu(dataset_menu, node)
        if tree_actions:
            self.add_tree_actions(dataset_menu)
            self.act_del.setEnabled(bool(node))
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
        if not self.cmd.currentwidget:
            return None
        if self.cmd.currentwidget.typename =='xy' and up:
            dsn = self.cmd.currentwidget.settings.yData
            node = self.model().tree.traverse(dsn)
            if node:
                self.selectionModel().clear()
                self.expand_node_path(node, select=True)
        return self.cmd.currentwidget
    
    def get_node_from_configuration(self, proxy):
        ins = proxy.instrument_obj
        uid = ins.measure['uid']
        prefix = '0:'
        used_prefixes = []
        if self.doc:
            used_prefixes = getUsedPrefixes(self.doc).values()
        for ln in used_prefixes: # LinkedFiles
            root = getattr(ln, 'conf', False)
            if not root: 
                continue
            ins = proxy.instrument_obj
            if not ins:
                logging.debug('Configuration does not have an active instrument!') 
                continue
            if ins.measure['uid'] == uid:
                prefix = ln.prefix
                break
        if self.doc and not ins:
            logging.error('Cannot find a LinkedFile for configuration', proxy)
            return False
        # Use instrument node where measure node is asked for
        if proxy['devpath'] =='measure':
            proxy = proxy.parent()
        node_path =  prefix + proxy['fullpath'][1:-1]
        node = self.doc.model.tree.traverse(node_path)
        if not node:
            logging.debug('Node not found while building menu', node_path)
            return False
        return node     
    
    def build_menu_from_configuration(self, proxy, menu=False):
        """Build a menu from a MisuraProxy or ConfigurationProxy"""
        if not menu:
            menu = QtGui.QMenu()
        # In live, out-of-test, doc is not defined:
        if not self.doc:
            menu.clear()
            for domain in self.domains:
                domain.build_nodoc_menu(menu, proxy)
            return menu
        node = self.get_node_from_configuration(proxy)
        menu = self.buildContextMenu(node, menu=menu)
        self.selectionModel().clear()
        self.expand_node_path(node, select=True)  
        return menu      
    
    @node
    def buildContextMenu(self, node=False, sel=[], menu=False, tree_actions=False):
        #TODO: way to buildContextMenu WITHOUT actually selecting the node!
        n = len(sel)
        if node is None or not node.parent:
            menu = self.update_base_menu(node, menu or self.base_menu, tree_actions=tree_actions)
        elif n>1:
            menu = self.update_multiary_menu(sel, menu or self.multi_menu)
        elif node.ds is False:
            # Identify a "summary" node
            if not node.parent.parent:
                menu = self.update_file_menu(node, menu or self.file_menu, tree_actions=tree_actions)
            # Identify a "sampleN" node
            elif node.name().startswith('sample'):
                menu = self.update_sample_menu(node, menu or self.sample_menu, tree_actions=tree_actions)
            else:
                menu = self.update_group_menu(node, menu or self.group_menu, tree_actions=tree_actions)
        # The DatasetEntry refers to a plugin
        elif hasattr(node.ds, 'getPluginData'):
            menu = self.update_derived_menu(node, menu or self.der_menu)
        # The DatasetEntry refers to a standard dataset
        elif n <= 1:
            menu = self.update_dataset_menu(node, menu or self.dataset_menu, tree_actions=tree_actions)
        # No active selection
        else:
            menu = self.update_base_menu(node, menu or self.base_menu, tree_actions=tree_actions)
        self.add_reset_plot_action(menu)
        return menu
    
    def hovered_node(self, node=False, qaction=False):
        logging.debug('hovered_node', node)
        if self.hovered!=node:
            self.expand_node_path(node, select=2)
            self.hovered = node 
        
    def build_recursive_menu(self, node, menu, qaction=False):
        """Build a recursive menu out of `menu`, starting from `node`"""
        # Build main menu
        menu.clear()
        self.buildContextMenu(node, menu=menu)
        # Select the corresponding node on the navigator when
        # an action is highlighted
        for a in menu.actions():
            a.hovered.connect(functools.partial(self.hovered_node, node))
        
        # Build visible children menu
        mod = self.model()
        idx0 = mod.indexFromNode(node)
        ch = mod.list_children(idx0)
        for idx in ch:
            subnode = mod.nodeFromIndex(idx)
            submenu = menu.addMenu(subnode.name())
            #submenu.aboutToShow.connect(partial(self.hovered_node, subnode))
            #submenu.aboutToHide.connect(partial(self.hovered_node, node))
            self.buildContextMenu(subnode, menu=submenu)
            
            # Recurse
            sub_menu_func = functools.partial(self.build_recursive_menu, 
                                    subnode, 
                                    submenu)
            submenu.aboutToShow.connect(sub_menu_func)


    def showContextMenu(self, pt):
        # Refresh currentwidget in cmd interface
        self.sync_currentwidget(update_navigator_selection=False)
        self.previous_selection = self.current_node_path
        sel = self.selectedIndexes()
        node = self.model().data(self.currentIndex(), role=Qt.UserRole)
        logging.debug('showContextMenu', node)
        menu = self.buildContextMenu(node, sel, tree_actions=True)
        
        # menu.popup(self.mapToGlobal(pt))
        # Synchronous call to menu, otherise selection is lost on live update
        self.pause(1)
        pt.setX(pt.x()+15)
        menu.setEnabled(True)
        menu.exec_(self.mapToGlobal(pt))
        logging.debug('Ended menu execution')
        self.pause(0)
        #self.update_view()
        
    def pause(self, do=True):
        self.model().pause(do)
        self.setEnabled(not do)
