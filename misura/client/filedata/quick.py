#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
from misura.canon.logger import Log as logging
from veusz.dialogs.plugin import PluginDialog

from veusz import document
from PyQt4.QtCore import Qt
from PyQt4 import QtGui, QtCore

import functools
from . import MisuraDocument, ImportParamsMisura, OperationMisuraImport
from entry import DatasetEntry
from .. import clientconf
from proxy import getFileProxy
import axis_selection
import numpy as np

ism = isinstance


def docname(ds):
    """Get dataset name by searching in parent document data"""
    for name, obj in ds.document.data.iteritems():
        if obj == ds:
            return name
    return None


def node(func):
    """Decorator for functions which should get currentIndex node if no arg is passed"""
    @functools.wraps(func)
    def node_wrapper(self, *a, **k):
        n = False
        keyword = True
        # Get node from named parameter
        if k.has_key('node'):
            n = k['node']
        # Or from the first unnamed argument
        elif len(a) >= 1:
            n = a[0]
            keyword = False
        # If node was not specified, get from currentIndex
        if n is False:
            n = self.model().data(self.currentIndex(), role=Qt.UserRole)
        elif isinstance(n, document.Dataset):
            n = docname(n)
        # If node was expressed as/converted to string, get its corresponding
        # tree entry
        if isinstance(n, str) or isinstance(n, unicode):
            logging.debug('%s %s', 'traversing node', n)
            n = str(n)
            n = self.model().tree.traverse(n)

        if keyword:
            k['node'] = n
        else:
            a = list(a)
            a[0] = n
            a = tuple(a)
        logging.debug(
            '%s %s %s %s %s', '@node with', n, type(n), isinstance(n, unicode))
        return func(self, *a, **k)
    return node_wrapper


def nodes(func):
    """Decorator for functions which should get a list of currentIndex nodes if no arg is passed"""
    @functools.wraps(func)
    def node_wrapper(self, *a, **k):
        n = []
        keyword = True
        # Get node from named parameter
        if k.has_key('nodes'):
            n = k['nodes']
        # Or from the first unnamed argument
        elif len(a) >= 1:
            n = a[0]
            keyword = False
        # If node was not specified, get from currentIndex
        if not len(n):
            n = []
            for idx in self.selectedIndexes():
                n0 = self.model().data(idx, role=Qt.UserRole)
                n.append(n0)
        if keyword:
            k['nodes'] = n
        else:
            a = list(a)
            a[0] = n
            a = tuple(a)
        logging.debug(
            '%s %s %s %s %s', '@nodes with', n, type(n), isinstance(n, unicode))
        return func(self, *a, **k)
    return node_wrapper


class QuickOps(object):

    """Quick interface for operations on datasets"""
    _mainwindow = False

    @property
    def mainwindow(self):
        if self._mainwindow is False:
            return self
        return self._mainwindow

    @node
    def intercept(self, node=False):
        """Intercept all curves derived/pertaining to the current object"""
        if ism(node, DatasetEntry):
            dslist = [node.path]
        elif hasattr(node, 'datasets'):
            # FIXME: needs paths
            dslist = node.children.keys()
        else:
            dslist = []
        from misura.client import plugin
        xnames = self.xnames(node, page='/time')
        xnames.append('')
        p = plugin.InterceptPlugin(target=dslist, axis='X', critical_x=xnames[0])
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.InterceptPlugin)
        self.mainwindow.showDialog(d)

    ###
    # File actions
    ###
    @node
    def viewFile(self, node=False):
        if not node.linked:
            return False
        doc = MisuraDocument(node.linked.filename)
        from misura.client import browser
        browser.TestWindow(doc).show()

    @node
    def closeFile(self, node=False):
        # FIXME: model no longer have a "tests" structure.
        lk = node.linked
        if not lk:
            logging.debug('%s %s', 'Node does not have linked file', node.path)
            return False
        for ds in self.doc.data.values():
            if ds.linked == lk:
                self.deleteData(ds)


    @node
    def reloadFile(self, node=False):
        logging.debug('%s', 'RELOADING')
        if not node.linked:
            return False
        logging.debug('%s', node.linked.reloadLinks(self.doc))


    def load_version(self, LF, version):
        # FIXME: VERSIONING!
        logging.debug('%s', 'LOAD VERSION')
        LF.params.version = version
        LF.reloadLinks(self.doc)

        fl = self.model().files
        logging.debug('%s %s', 'got linked files', self.model().files[:])

    @node
    def commit(self, node=False):
        """Write datasets to linked file. """
        name, st = QtGui.QInputDialog.getText(
            self, "Version Name", "Choose a name for the data version you are saving:")
        if not st:
            logging.debug('%s', 'Aborted')
            return
        logging.debug('%s %s', 'Committing data to', node.filename)
        node.commit(unicode(name))


    ###
    # Sample actions
    ###
    @node
    def deleteChildren(self, node=False):
        """Delete all children of node."""
        logging.debug('%s %s %s', 'deleteChildren', node, node.children)
        for sub in node.children.values():
            if not sub.ds:
                continue
            self.deleteData(sub)
#

    @node
    def showPoints(self, node=False):
        """Show characteristic points"""
        from misura.client import plugin
        p = plugin.ShapesPlugin(sample=node)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ShapesPlugin)
        self.mainwindow.showDialog(d)

    @node
    def hsm_report(self, node=False):
        """Execute HsmReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_hsm.vsz', 'Vol')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)

    @node
    def horizontal_report(self, node=False):
        """Execute HorzizontalReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_horizontal.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)

    @node
    def vertical_report(self, node=False):
        """Execute VerticalReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_vertical.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)

    @node
    def flex_report(self, node=False):
        """Execute FlexReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_flex.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)

    @node
    def render(self, node=False):
        """Render video from `node`"""
        from misura.client import video
        sh = getFileProxy(node.linked.filename)
        pt = '/' + \
            node.path.replace(node.linked.prefix, '').replace('summary', '')
        v = video.VideoExporter(sh, pt)
        v.exec_()
        sh.close()

    ###
    # Dataset actions
    ###
    def _load(self, node):
        """Load or reload a dataset"""
        op = OperationMisuraImport.from_dataset_in_file(
            node.path, node.linked.filename)
        self.doc.applyOperation(op)

    @node
    def load(self, node=False):
        logging.debug('%s %s', 'load', node)
        if node.linked is None:
            logging.debug('%s %s', 'Cannot load: no linked file!', node)
            return
        if not node.linked.filename:
            logging.debug('%s %s', 'Cannot load: no filename!', node)
            return
        if len(node.data) > 0:
            logging.debug('%s %s', 'Unloading', node.path)
            # node.ds.data = []
            ds = node.ds
            self.deleteData(node=node)
            # self.deleteData(node=node, remove_dataset=False, recursive=False)
            ds.data = np.array([])
            self.doc.available_data[node.path] = ds
            self.model().pause(False)
            self.doc.setModified()

            return
        self._load(node)

        pass

    @node
    def thermalLegend(self, node=False):
        """Write thermal cycle onto a text label"""
        from misura.client import plugin
        p = plugin.ThermalCyclePlugin(test=node)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.ThermalCyclePlugin)
        self.mainwindow.showDialog(d)

    @node
    def setInitialDimension(self, node=False):
        """Invoke the initial dimension plugin on the current entry"""
        logging.debug('%s %s %s', 'Searching dataset name', node, node.path)
        n = self.doc.datasetName(node.ds)
        ini = getattr(node.ds, 'm_initialDimension', False)
        if not ini:
            ini = 100.
        logging.debug('%s %s %s', 'Invoking InitialDimensionPlugin', n, ini)
        from misura.client import plugin
        p = plugin.InitialDimensionPlugin(ds=n, ini=ini)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.InitialDimensionPlugin)
        self.mainwindow.showDialog(d)

    @node
    def convertPercentile(self, node=False):
        """Invoke the percentile plugin on the current entry"""
        n = self.doc.datasetName(node.ds)
        from misura.client import plugin
        p = plugin.PercentilePlugin(ds=n, propagate=True)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.PercentilePlugin)
        self.mainwindow.showDialog(d)

    @node
    def set_unit(self, node=False, convert=False):
        logging.debug('%s %s %s %s', 'set_unit:', node, node.unit, convert)
        if node.unit == convert or not convert or not node.unit:
            logging.debug('%s', 'set_unit: Nothing to do')
            return
        n = self.doc.datasetName(node.ds)
        from misura.client import plugin
        p = plugin.UnitsConverterTool(ds=n, convert=convert, propagate=True)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.UnitsConverterTool)
        self.mainwindow.showDialog(d)

    @node
    def deleteData(self, node=False, remove_dataset=True, recursive=True):
        """Delete a dataset and all depending graphical widgets."""
        node_path = node.path
        # Remove and exit if dataset was only in available_data
        if self.doc.available_data.has_key(node_path):
            self.doc.available_data.pop(node_path)
            if not self.doc.data.has_key(node_path):
                return True
        # Remove and exit if no plot is associated
        if not self.model().plots['dataset'].has_key(node_path):
            if remove_dataset:
                self.doc.deleteDataset(node_path)
                self.doc.setModified()

            return True

        plots = self.model().plots['dataset'][node_path]
        # Collect involved graphs
        graphs = []
        # Collect plots to be removed
        remplot = []
        # Collect axes which should be removed
        remax = []
        # Collect objects which refers to xData or yData
        remobj = []
        # Remove associated plots
        for p in plots:
            p = self.doc.resolveFullWidgetPath(p)
            g = p.parent
            if g not in graphs:
                graphs.append(g)
            remax.append(g.getChild(p.settings.yAxis))
            remplot.append(p)

        # Check if an ax is referenced by other plots
        for g in graphs:
            for obj in g.children:
                if obj.typename == 'xy':
                    y = g.getChild(obj.settings.yAxis)
                    if y is None:
                        continue
                    # If the axis is used by an existent plot, remove from the
                    # to-be-removed list
                    if y in remax and obj not in remplot:
                        remax.remove(y)
                    continue
                # Search for xData/yData generic objects

                for s in ['xData', 'yData', 'xy']:
                    o = getattr(obj.settings, s, None)
                    refobj = g.getChild(o)
                    if refobj is None:
                        continue
                    if refobj not in plots + [node_path]:
                        continue
                    if obj not in remplot + remax + remobj:
                        remobj.append(obj)

        # Remove object and unreferenced axes
        for obj in remplot + remax + remobj:
            logging.debug('%s %s %s', 'Removing obj', obj.name, obj.path)
            obj.parent.removeChild(obj.name)
        # Finally, delete dataset
        if remove_dataset:
            self.doc.deleteDataset(node_path)
            logging.debug('%s %s', 'deleted', node_path)

        # Recursive call over derived datasets
        if recursive:
            for sub in node.children.itervalues():
                self.deleteData(sub, remove_dataset, recursive)
        self.doc.setModified()
        return True

    @nodes
    def deleteDatas(self, nodes=[]):
        """Call deleteData on each selected node"""
        for n in nodes:
            self.deleteData(node=n)

    def xnames(self, y, page=False):
        """Get X dataset name for Y node y, in `page`"""
        logging.debug('%s %s %s %s', 'XNAMES', y, type(y), y.path)
        logging.debug('%s %s', 'y.linked', y.linked)
        logging.debug('%s %s', 'y.parent.linked', y.parent.linked)

        if page == False:
            page = self.model().page
        lk = y.linked if y.linked else y.parent.linked

        xname = axis_selection.get_best_x_for(y.path, lk.prefix, self.doc.data, page)

        return [xname]


    def dsnode(self, node):
        """Get node and corresponding dataset"""
        ds = node
        if isinstance(node, DatasetEntry):
            ds = node.ds
        return ds, node

    @node
    def plot(self, node=False):
        """Slot for plotting by temperature and time the currently selected entry"""
        pt = self.model().is_plotted(node.path)
        if pt:
            logging.debug('%s %s', 'UNPLOTTING', node)
            self.deleteData(node=node, remove_dataset=False, recursive=False)
            return
        # Load if no data
        if len(node.data) == 0:
            self.load(node)
        yname = node.path

        from misura.client import plugin
        # If standard page, plot both T,t
        page = self.model().page
        if page.startswith('/temperature/') or page.startswith('/time/'):
            logging.debug('%s %s', 'Quick.plot', page)
            # Get X temperature names
            xnames = self.xnames(node, page='/temperature')
            assert len(xnames) > 0
            p = plugin.PlotDatasetPlugin()
            p.apply(self.cmd, {
                    'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': '/temperature/temp'})

            # Get time datasets
            xnames = self.xnames(node, page='/time')
            assert len(xnames) > 0
            p = plugin.PlotDatasetPlugin()
            p.apply(self.cmd, {
                    'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': '/time/time'})
        else:
            if page.startswith('/report'):
                page = page + '/temp'
            logging.debug('%s %s', 'Quick.plot on currentwidget', page)
            xnames = self.xnames(node, page=page)
            assert len(xnames) > 0
            p = plugin.PlotDatasetPlugin()
            p.apply(
                self.cmd, {'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': page})
        self.doc.setModified()

    @node
    def edit_dataset(self, node=False):
        """Slot for opening the dataset edit window on the currently selected entry"""
        ds, y = self.dsnode(node)
        name = node.path
        logging.debug('%s %s', 'name', name)
        dialog = self.mainwindow.slotDataEdit(name)
        if ds is not y:
            dialog.slotDatasetEdit()

    @node
    def smooth(self, node=False):
        """Call the SmoothDatasetPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)
        from misura.client import plugin
        p = plugin.SmoothDatasetPlugin(
            ds_in=node.path, ds_out=node.m_name + '/sm', window=int(w))
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.SmoothDatasetPlugin)
        self.mainwindow.showDialog(d)

    @node
    def coefficient(self, node=False):
        """Call the CoefficientPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)
        ds_x = self.xnames(node, '/temperature')[0]
        ini = getattr(ds, 'm_initialDimension', 0)
        if getattr(ds, 'm_percent', False):
            ini = 0. # No conversion if already percent
        from misura.client import plugin
        p = plugin.CoefficientPlugin(
            ds_y=node.path, ds_x=ds_x, ds_out=node.m_name + '/cf', smooth=w, percent=ini)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.CoefficientPlugin)
        self.mainwindow.showDialog(d)

    @node
    def derive(self, node=False):
        """Call the DeriveDatasetPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)

        ds_x = self.xnames(node, "/time")[0]  # in current page

        from misura.client import plugin
        p = plugin.DeriveDatasetPlugin(
            ds_y=node.path, ds_x=ds_x, ds_out=node.m_name + '/d', smooth=w)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.DeriveDatasetPlugin)
        self.mainwindow.showDialog(d)

    @node
    def calibration(self, node=False):
        """Call the CalibrationFactorPlugin on the current node"""
        ds, node = self.dsnode(node)

        T = self.xnames(node, "/temperature")[0]  # in current page

        from misura.client import plugin
        p = plugin.CalibrationFactorPlugin(d=node.path, T=T)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.CalibrationFactorPlugin)
        self.mainwindow.showDialog(d)

    @nodes
    def correct(self, nodes=[]):
        """Call the CurveOperationPlugin on the current nodes"""
        ds0, node0 = self.dsnode(nodes[0])
        T0 = node0.linked.prefix + 'kiln/T'
        ds1, node1 = self.dsnode(nodes[1])
        T1 = node1.linked.prefix + 'kiln/T'
        from misura.client import plugin
        p = plugin.CurveOperationPlugin(
            ax=T0, ay=node0.path, bx=T1, by=node1.path)
        # TODO: TC comparison?
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.CurveOperationPlugin)
        self.mainwindow.showDialog(d)

    @nodes
    def surface_tension(self, nodes):
        """Call the SurfaceTensionPlugin.
        - 1 node selected: interpret as a sample and directly use its beta,r0,Vol,T datasets
        - 2 nodes selected: interpret as 2 samples and search the node having beta,r0 children; use dil/T from the other
        - 4 nodes selected: interpret as separate beta, r0, Vol, T datasets and try to assign based on their name
        - 5 nodes selected: interpret as separate (beta, r0, T) + (dil, T) datasets and try to assign based on their name and path
        """
        if len(nodes) > 1:
            logging.debug('%s', 'Not implemented')
            return False
        smp = nodes[0].children
        dbeta, nbeta = self.dsnode(smp['beta'])
        beta = nbeta.path
        dR0, nR0 = self.dsnode(smp['r0'])
        R0 = nR0.path
        ddil, ndil = self.dsnode(smp['Vol'])
        dil = ndil.path
        T = nbeta.linked.prefix + 'kiln/T'
        out = nbeta.linked.prefix + 'gamma'
        if not self.doc.data.has_key(T):
            T = ''
        # Load empty datasets
        if len(dbeta) == 0:
            self._load(nbeta)
        if len(dR0) == 0:
            self._load(nR0)
        if len(ddil) == 0:
            self._load(ndil)
        from misura.client import plugin
        cls = plugin.SurfaceTensionPlugin
        p = cls(beta=beta, R0=R0, T=T,
                dil=dil, dilT=T, ds_out=out, temperature_dataset=self.doc.data[T].data)
        d = PluginDialog(self.mainwindow, self.doc, p, cls)
        self.mainwindow.showDialog(d)

    @node
    def keep(self, node=False):
        """Inverts the 'keep' flag on the current dataset,
        causing it to be saved (or not) on the next file commit."""
        ds, node = self.dsnode(node)
        cur = getattr(ds, 'm_keep', False)
        ds.m_keep = not cur

    @node
    def save_on_current_version(self, node=False):
        proxy = getFileProxy(node.linked.filename)
        prefix = node.linked.prefix
        try:
            proxy.save_data(node.ds.m_col, node.ds.data, self.model().doc.data[prefix + "t"].data)
        except Exception as e:
            message = "Impossible to save data.\n\n" + str(e)
            QtGui.QMessageBox.warning(None,'Error', message)
        proxy.close()

    @node
    def colorize(self, node=False):
        """Set/unset color markers."""
        plotpath = self.model().is_plotted(node.path)
        if not len(plotpath) > 0:
            return False
        x = self.xnames(node)[0]
        from misura.client import plugin
        p = plugin.ColorizePlugin(curve=plotpath[0], x=x)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ColorizePlugin)
        self.mainwindow.showDialog(d)

    @node
    def save_style(self, node=False):
        """Save current curve color, style, marker and axis ranges and scale."""
        # TODO: save_style
        pass

    @node
    def delete_style(self, node=False):
        """Delete style rule."""
        # TODO: delete_style
        pass

    @node
    def change_rule(self, node=False, act=0):
        """Change current rule"""
        # TODO: change_rule
        pass

    ####
    # Derived actions
    @node
    def overwrite(self, node=False):
        """Overwrite the parent dataset with a derived one."""
        ds, node = self.dsnode()
        from misura.client import plugin
        p = plugin.OverwritePlugin(
            a=node.parent.path, b=node.path, delete=True)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.OverwritePlugin)
        self.mainwindow.showDialog(d)
