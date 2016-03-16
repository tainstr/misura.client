#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Rich, hierarchical representation of opened tests and their datasets"""
from misura.canon.logger import Log as logging
import sip
sip.setapi('QString', 2)
from veusz import document
import veusz.setting
import veusz.utils
from .. import _
from entry import DatasetEntry

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import functools
from misura.client.iutils import namingConvention
from misura.canon.csutil import find_nearest_val
from entry import iterpath, NodeEntry, dstats

from misura.client.iutils import get_plotted_tree
from misura.canon.csutil import lockme
import threading


def ism(obj, cls):
    return getattr(obj, 'mtype', False) == cls.mtype


def resolve_plugin(doc, ds, ent, name=False):
    # Check if already present
    r = ent.get(id(ds), False)
    if r is not False:
        return ent, r
    # Create a main DatasetEntry instance
    if not isinstance(ds, document.datasets.Dataset1DPlugin):
        entry = DatasetEntry(doc, ds)
        ent[entry.mid] = entry
        return ent, entry
    return ent, False

from veusz.setting import controls
void = None
voididx = QtCore.QModelIndex()


def get_item_icon(plotwg):
    style = plotwg.settings.get('PlotLine').get('style').val
    i = veusz.setting.LineStyle._linestyles.index(style)
    line_icon = controls.LineStyle._icons[i]
    marker = plotwg.settings.get('marker').val
    if marker is False or str(marker)=='none':
        return line_icon
    i = veusz.utils.MarkerCodes.index(marker)
    marker_icon = controls.Marker._icons[i]
    
    combined = QtGui.QIcon()
    pix = QtGui.QPixmap(24, 16)
    pix.fill()
    marker_pix = marker_icon.pixmap(10,10)
    line_pix = line_icon.pixmap(24, 8)
    painter = QtGui.QPainter(pix)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.drawPixmap(0, 8, line_pix)
    painter.drawPixmap(14, 0, marker_pix)
    
    painter.end()
    combined.addPixmap(pix)
    
    return combined

class DocumentModel(QtCore.QAbstractItemModel):
    changeset = 0
    _plots = False

    def __init__(self, doc, status=dstats, refresh=True, cols=2):
        QtCore.QAbstractItemModel.__init__(self)
        self.keys = set()
        self.available_keys = set()
        self._lock = threading.Lock()
        self.ncols = cols
        self.status = status
        self.doc = doc
        self.tree = NodeEntry()

        if refresh:
            self.refresh()
        else:
            self.tree = self.doc.model.tree
        controls.Marker._generateIcons()
        controls.LineStyle._generateIcons()

        self.counter = 0



    idx = 0

    def set_idx(self, t):
        if self.paused:
            return False
        logging.debug('%s %s', 'DocumentModel.set_idx', t)
        # TODO: convert to time index
        tds = self.doc.data.get('t', False)
        if tds is False:
            return False
        n = find_nearest_val(tds.data, t)
        self.idx = n
# 		self.emit(QtCore.SIGNAL('dataChanged(QModelIndex,QModelIndex)'),self.index(0,1),self.index(n,1))
        self.emit(QtCore.SIGNAL('modelReset()'))
        return True

    def set_time(self, t):
        """Changes current values to requested time `t`"""
        idx = find_nearest_val(self.doc.data['0:t'].data, t, seed=self.idx)
        logging.debug('%s %s %s', 'Setting time t', t, idx)
        self.set_idx(idx)
        return True

    paused = False

    def pause(self, do=True):
        logging.debug('%s %s', 'Set paused', do)
        self.paused = do
        if do:
            self.disconnect(
                self.doc, QtCore.SIGNAL("signalModified"), self.refresh)
        else:
            self.connect(self.doc, QtCore.SIGNAL("signalModified"), self.refresh)

    page = '/temperature/temp'

    def set_page(self, page):
        if self.paused:
            return False
        if page.startswith('/temperature'):
            page = '/temperature/temp'
        elif page.startswith('/time'):
            page = '/time/time'
        self.page = page
        self.emit(QtCore.SIGNAL('modelReset()'))
        return True

    @property
    def plots(self):
        if self.changeset != self.doc.changeset or self._plots is False:
            self._plots = get_plotted_tree(self.doc.basewidget)
            self.changeset = self.doc.changeset
        return self._plots

    @lockme
    def refresh(self, force=False):
        if not force:
            if self.paused:
                logging.debug('%s %s', 'NOT REFRESHING MODEL', self.paused)
                return False
            elif self.keys == set(self.doc.data.keys()) and self.available_keys == set(self.doc.available_data.keys()):
                logging.debug('model.refresh(): NOTHING CHANGED')
                return False

        logging.debug('%s %s', 'REFRESHING MODEL', self.paused)
        self.paused = True
        self.doc.suspendUpdates()
        self.emit(QtCore.SIGNAL('beginResetModel()'))
        new_tree = NodeEntry()
        new_tree.set_doc(self.doc)
        self.tree = new_tree
        self._lock.release()

        self.emit(QtCore.SIGNAL('endResetModel()'))
        self.paused = False

        self.changeset = self.doc.changeset
        self.keys = set(self.doc.data.keys())
        self.available_keys = set(self.doc.available_data.keys())
        self.doc.enableUpdates()
        self.emit(QtCore.SIGNAL('modelReset()'))
        return True

    def is_plotted(self, key, page=False):
        plots = self.plots['dataset'].get(key, [])
        out = []
        if not page:
            page = self.page
        for p in plots:
            if p.startswith(page):
                out.append(p)
        return out

    def nodeFromIndex(self, index):
        if index.isValid():
            node = self.tree.traverse(str(index.internalPointer()))
            if not node:
                print '######### nodeFromIndex',index.internalPointer()
            return node

        else:
            # print 'nodeFromIndex
            # print 'invalid ', index.row(),index.column(),index.internalPointer(), " <-----------------"
            return self.tree

    @lockme
    def rowCount(self, parent):
        node = self.nodeFromIndex(parent)
        if node is False:
            return 0
        rc = len(node.recursive_status(self.status, depth=0))
        return rc

    def columnCount(self, parent):
        return self.ncols

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return _('Dataset')
            # TODO!
            return _('Value')
        
        
    def decorate(self, ent, role):
        """Find text color and icon decorations for dataset ds"""
        if not ent.ds:
            return void
        plotpath = self.is_plotted(ent.path)
        if len(plotpath) == 0:
            plotwg = False
        else:
            plotwg = self.doc.resolveFullWidgetPath(plotpath[0])

        if role == Qt.DecorationRole:
            # No plots
            if plotwg is False:
                return void
            return get_item_icon(plotwg)
        if role == Qt.ForegroundRole:
            if plotwg is False:
                return void
            # Retrieve plot line color
            xy = plotwg.settings.get('PlotLine').get('color').color()
#				print ' ForegroundRole' ,node.m_var,xy.value()
            return QtGui.QBrush(xy)

        if role == Qt.FontRole:
            current_font = QtGui.QFont()
            current_font.setBold(len(ent.data) > 0 and 0 in self.status)


            return current_font
        return void

    @lockme
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return void

        if role not in [Qt.DisplayRole, Qt.ForegroundRole, Qt.DecorationRole, Qt.UserRole, Qt.FontRole]:
            return void
        col = index.column()
        row = index.row()
        node = self.nodeFromIndex(index)
        if role == Qt.UserRole:
            return node
        if col == 0:
            if role in [Qt.ForegroundRole, Qt.DecorationRole, Qt.FontRole]:
                return self.decorate(node, role)
            if isinstance(node, DatasetEntry):
                if role == Qt.DisplayRole:
                    t = "%s"

                    if getattr(node.ds, 'm_label', False):
                        t = node.ds.m_label + " (%s)"

                    t = t % node.legend

                    return t
            elif isinstance(node, NodeEntry):
                r = node.name()
                LF = node.linked
                if (node.parent and LF) and not node.parent.parent:
                    r = getattr(LF.conf, LF.instrument)
                    r.connect()
                    r = r.measure['name']
                    if len(LF.prefix):
                        r += ', ({})'.format(LF.prefix)
                if role == Qt.DisplayRole:
                    return r
                return void

        else:
            if isinstance(node, DatasetEntry):
                d = node.ds.data
                if len(d) > self.idx:
                    #					print 'Retrieving data index',self.idx
                    return str(node.ds.data[self.idx])
        return void

    @lockme
    def index(self, row, column, parent=voididx):
        parent = self.nodeFromIndex(parent)
        if not (isinstance(parent, DatasetEntry) or isinstance(parent, NodeEntry)):
            logging.debug('%s %s', 'child ERROR', parent)
            return voididx
        assert row >= 0
        lst = parent.recursive_status(self.status, depth=0)
        if row >= len(lst):
            logging.debug('%s %s %s', 'WRONG ROW', row, len(lst))
            return voididx
        assert row < len(lst), 'index() ' + str(parent) + \
            str(row) + str(lst) + str(self.status)
        child = lst[row]
        # Update entries dictionary ???
        self.doc.ent[id(child)] = child
        idx = self.createIndex(row, column, child.model_path)
        return idx

    @lockme
    def parent(self, child):
        child = self.nodeFromIndex(child)
        if not (isinstance(child, DatasetEntry) or isinstance(child, NodeEntry)):
            # 			print 'parent ERROR',child,type(child)
            return voididx
        parent = child.parent
        if parent is False:
            # 			print  'parent ERROR no parent',child,child.parent
            return voididx
        # Grandpa
        sup = parent.parent
        if sup is False:
            # 			print 'parent ERROR no grandpa'
            return voididx
        lst = sup.recursive_status(self.status, depth=0)
        if parent not in lst:
            # print 'parent() child not in list',child.path,[d.path for d in
            # lst]
            return voididx
        # Position of parent in grandpa
        row = lst.index(parent)
        return self.createIndex(row, 0, parent.model_path)

    def indexFromNode(self, node):
        """Return the model index corresponding to node. Useful in ProxyModels"""
        parent = self.parent(node)
        row = parent.recursive_status(self.status, depth=0).index(node)
        return self.createIndex(row, 0, parent.model_path)

    def index_path(self, node):
        """Returns the sequence of model indexes starting from a node."""
        obj = node
        n = []
        while obj != self.tree:
            n.append(obj)
            obj = obj.parent
            if obj is None:
                break

        n.reverse()
        jdx = []
        for obj in n:
            # Find position in siblings
            i = obj.parent.recursive_status(self.status, depth=0).index(obj)
            jdx.append(self.createIndex(i,0,obj.model_path))
        logging.debug('%s %s', 'index_path', jdx)
        return jdx

    #####
    # Drag & Drop
    def mimeTypes(self):
        return ["text/plain"]

    def mimeData(self, indexes):
        out = []
        for index in indexes:
            node = self.nodeFromIndex(index)
            out.append(node.path)
        logging.debug('%s %s', 'mimeData', out)
        dat = QtCore.QMimeData()
        dat.setData("text/plain", ';'.join(out))
        return dat

    def flags(self, index):
        f = QtCore.QAbstractItemModel.flags(self, index)
        node = self.nodeFromIndex(index)
        if isinstance(node, DatasetEntry):
            return QtCore.Qt.ItemIsDragEnabled | f
        return f

    #######################################
    # FROM HIERARCHY
    # TODO: adapt or move to QuickOps
    def hide(self, name):
        item = self.tree.traverse(name)
        if item.status == dstats.hidden:
            return False
        item.status = 0
        return True

    def show(self, name):
        item = self.tree.traverse(name)
        if item.status == dstats.visible:
            return False
        item.status = 1
        return True

    def load(self, name):
        item = self.traverse(name)
        if item.status > dstats.available:
            return False
        item.status = 0
        return True

    def hide_show(self, col, do=None, emit=True):
        logging.debug('%s %s %s %s', 'RowView.hide_show', col, do, emit)
        col = str(col)
        if do == None:
            item = self.tree.traverse(col)
            do = item.status > 0
        if do:
            self.show(col)
        else:
            self.hide(col)
        if emit:
            self.emit(QtCore.SIGNAL('hide_show_col(QString,int)'), col, do)
        self.model().refresh()

    ############
    # Menu creation utilities

    def build_datasets_menu(self, menu, func, checkfunc=False):
        """Builds a hierarchical tree menu for loaded datasets.
        Menu actions will trigger `func`, and their checked status is provided by `checkfunc`."""
        self.refresh()
        menu.clear()
        curveMap = {}
        for name, ds in self.doc.data.iteritems():
            if len(ds.data) == 0:
                continue
            func1 = functools.partial(func, name)
            self.add_menu(name, menu, func1, curveMap, checkfunc=checkfunc)

        # Prepare the 'More...' menu, but not actually populate it until
        # hovered
        more = menu.addMenu('More...')
        bam = lambda: self.build_available_menu(more, func, checkfunc)
        more.connect(more, QtCore.SIGNAL('aboutToShow()'), bam)
        alterMap = {'more': more, 'bam': bam}  # keep references

        # NOTICE: must keep these referenced by the caller
        return curveMap, alterMap

    def build_available_menu(self, menu, func, checkfunc=lambda ent: ent.status > 1):
        """Builds a menu of available (but empty) datasets, which can be loaded upon request by calling `func`.
        Their action checked status might is provided by `checkfunc`."""
        menu.clear()
        curveMap1 = {}
        for name, ds in self.doc.data.iteritems():
            if len(ds.data) > 0:
                continue
            func1 = functools.partial(func, name)
            self.add_menu(
                name, menu, func1, curveMap1, checkfunc=lambda foo: False)
        # NOTICE: must keep these referenced by the caller
        return curveMap1

    splt = '/'

    def add_menu(self, name, menu, func=lambda: 0, curveMap={}, hidden_curves=[], checkfunc=False):
        # 		print 'add_menu pre',name,curveMap
        if checkfunc is False:
            def checkfunc(ent):
                return self.plots['dataset'].has_key(name)
        var, smp = namingConvention(name, splt=self.splt)
        # Do not show hidden curves
        if var in hidden_curves:
            return False
        # Recursively create parent menus
        for sub, parent, leaf in iterpath(name):
            if leaf is True:
                break
            if not parent:
                continue
#				child=sub
            else:
                child = self.splt.join([parent, sub])
            m = curveMap.get(child, False)
            if m is False:
                # 				print 'creating intermediate menu',sub,child
                m = menu.addMenu(sub)
                curveMap[child] = m
            menu = m
        act = menu.addAction(sub, func)
        act.setCheckable(True)
        act.setChecked(checkfunc(name))
# 		print 'add_menu',name,sub,parent,curveMap
        return act

    def matching(self, pt):
        """Get the matching ax"""
        s = self.doc.resolveFullSettingPath(pt + '/linked')
        if not s.get():
            return ''
        s = self.doc.resolveFullSettingPath(pt + '/linkedaxis')
        return s.get()

    def build_axes_menu(self, menu):
        """Builds a two-level hierarchy from all visible axes in a plot.
        The first level contains axes which does not match any other ax (match setting is empty).
        The second level contains both any other non matched axis, and every other axis
        which matches the parent first level axis."""
        menu.clear()
        axs = self.plots['axis'].keys()
        logging.debug('%s %s', 'AXES', axs)
        axmap = {}
        axs1 = []  # First level (no match setting)
        axs2 = {}  # Second level (matching)
        # Populate first-level menu
        for pt in axs:
            # discard axis not in current page
            if not pt.startswith(self.page):
                logging.debug('%s %s %s', 'Ax: Other page', pt, self.page)
                continue
            sp = pt.split('/')
            axname = sp.pop(-1)
            basename = ('/'.join(sp))
#  			axmap[pt]=menu.addMenu(axname)
            m = self.matching(pt)
            if m == '':
                axs1.append(pt)
            else:
                pt0 = basename + '/' + m
                axs2[pt] = pt0

        for pt in axs1:
            axname = pt.split('/')[-1]
            axmap[pt] = menu.addMenu(axname)

        # Populate second-level menu with assigned
        for pt2, pt in axs2.iteritems():
            # Add the matched ax to the first-level matching ax
            func = functools.partial(self.match_axes, pt2, pt)
            act = axmap[pt].addAction(pt2.split('/')[-1], func)
            act.setCheckable(True)
            act.setChecked(True)

        # Add unassigned to second level menus
        for pt, submenu in axmap.iteritems():
            if pt not in axs1:
                continue
            for pt1 in axs1:
                if pt == pt1:
                    continue
                func = functools.partial(self.match_axes, pt, pt1)
                act = submenu.addAction(pt1.split('/')[-1], func)
                act.setCheckable(True)
                act.setChecked(False)
        # NOTICE: must keep these referenced by the caller
        return axmap

    def match_axes(self, first, second):
        """Add `first`-level axis to the list of matched axes of the `second`-level axis.
        The first-level axis will remain first-level.
        The `second` will become `second`-level and will be listed
        in every other first-level axis referenced in its match setting."""

        logging.debug('matching %s %s', first, second)
        s = self.doc.resolveFullSettingPath(first + '/linked')
        s1 = self.doc.resolveFullSettingPath(first + '/linkedaxis')
        ops = []
        if self.matching(first):
            print 'Unsetting', first, second
            ops.append(document.OperationSettingSet(s, False))
            ops.append(document.OperationSettingSet(s1, ''))
            s.set(False)
            s1.set('')
        else:
            print 'Setting', first, second, self.matching(first)
            ops.append(document.OperationSettingSet(s, True))
            ops.append(document.OperationSettingSet(s1, second.split('/')[-1]))
        self.doc.applyOperation(
            document.OperationMultiple(ops, descr=_('Axis match')))
