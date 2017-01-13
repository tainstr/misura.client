#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.plugin.domains import node, nodes

from ..filedata import DatasetEntry
from .. import axis_selection
import numpy as np

from PyQt4 import QtGui

ism = isinstance




class QuickOps(object):

    """Quick interface for operations on datasets"""
    _mainwindow = False

    @property
    def mainwindow(self):
        if self._mainwindow is False:
            return self
        return self._mainwindow
    
    def get_page_number_from_path(self, page_name):
        # Search current page
        page_num = -1
        for wg in self.doc.basewidget.children:
            page_num += 1
            if wg.name == page_name:
                return page_num
        return -1
            

    @node
    def deleteChildren(self, node=False):
        """Delete all children of node."""
        logging.debug('deleteChildren', node, node.children)
        confirmation = QtGui.QMessageBox.warning(self, "Delete nodes",
                       "You are about to delete data. Do you confirm?",
                       QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
        if confirmation != QtGui.QMessageBox.Yes:
            return

        for sub in node.children.values():
            if not sub.ds:
                continue
            self.deleteData(sub)
#
    def _load(self, node):
        """Load or reload a dataset"""
        self.doc._load(node.path, node.linked.filename, version=node.linked.version)
        
    @node
    def load_rule(self, node, rule, overwrite=True):
        self.doc.load_rule(node.linked.filename, rule, overwrite=overwrite)
        
    @node
    def load(self, node=False):
        logging.debug('load', node)
        if node.linked is None:
            logging.error('Cannot load: no linked file!', node)
            return
        if not node.linked.filename:
            logging.error('Cannot load: no filename!', node)
            return
        if len(node.data) > 0:
            logging.debug('Unloading', node.path)
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
            if len(xnames) > 0:
                p = plugin.PlotDatasetPlugin()
                p.apply(self.cmd, {
                        'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': '/temperature/temp'})

            # Get time datasets
            xnames = self.xnames(node, page='/time')
            if len(xnames) > 0:
                p = plugin.PlotDatasetPlugin()
                p.apply(self.cmd, {
                        'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': '/time/time'})
        else:
            if page.startswith('/report'):
                page = page + '/temp'
            logging.debug('%s %s', 'Quick.plot on currentwidget', page)
            xnames = self.xnames(node, page=page)
            assert len(xnames) > 0
            args = {'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': self.cmd.currentwidget.path}
            if not self.cmd.currentwidget.path.startswith(page):
                logging.debug('FORCING currentwidget to', page, 'was', self.cmd.currentwidget.path)
                args['currentwidget'] = page
            p = plugin.PlotDatasetPlugin()
            p.apply(self.cmd, args)
        self.doc.setModified()
        return True

    @node
    def deleteData(self, node=False, remove_dataset=True, recursive=True):
        """Delete a dataset and all depending graphical widgets."""
        self.model().pause(0)
        if not node:
            return True
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


    def widget_path_for(self, node):
        result = '/'
        full_path = self.doc.model.is_plotted(node.path)
        if full_path:
            result = full_path[0]

        return result

    def xnames(self, y, page=False):
        """Get X dataset name for Y node y, in `page`"""
        if page == False:
            page = self.model().page
        lk = y.linked if y.linked else y.parent.linked
        try:
            self.doc.resolveFullWidgetPath(page)
        except:
            logging.error('No page', page)
            return []
        xname = axis_selection.get_best_x_for(y.path, lk.prefix, self.doc.data, page)

        return [xname]

    def dsnode(self, node):
        """Get node and corresponding dataset"""
        ds = node
        if isinstance(node, DatasetEntry):
            ds = node.ds
        return ds, node


