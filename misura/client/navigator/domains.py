#!/usr/bin/python
# -*- coding: utf-8 -*-

import functools

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.plugin import navigator_domains, NavigatorDomain, node, nodes
from misura.canon.plugin import domains as canon_domains
from misura.canon.indexer import SharedFile

from .. import conf, units, iutils
from veusz.dialogs.plugin import PluginDialog

from PyQt4 import QtGui, QtCore
canon_domains.QtUserRole = QtCore.Qt.UserRole

from .. import _
from ..filedata import MisuraDocument
from ..filedata import DatasetEntry
from ..filedata import getFileProxy
from ..fileui import VersionMenu
from ..clientconf import confdb, rule_suffixes
from ..widgets.aTable import table_model_export



class DataNavigatorDomain(NavigatorDomain):

    def __init__(self, *a, **k):
        super(DataNavigatorDomain, self).__init__(*a, **k)
        self.configuration_windows = {}
        self.data_tables = {}
        self.test_windows = {}
        
    @node
    def edit_dataset(self, node=False):
        """Slot for opening the dataset edit window on the currently selected entry"""
        ds, y = self.dsnode(node)
        name = node.path
        logging.debug('name', name)
        dialog = self.mainwindow.slotDataEdit(name)
        if ds is not y:
            dialog.slotDatasetEdit()
            
    def create_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_V), 
                        self.navigator, 
                        self.edit_dataset,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)
        
        
    @node
    def viewFile(self, node=False):
        if not node.linked:
            return False
        win = self.test_windows.get(node.linked.filename, False)
        if win:
            win.show()
            return
        doc = MisuraDocument(node.linked.filename)
        from misura.client import browser
        win = browser.TestWindow(doc)
        win.show()
        self.test_windows[node.linked.filename] = win

    @node
    def closeFile(self, node=False):
        # FIXME: model no longer have a "tests" structure.
        lk = node.linked
        if not lk:
            logging.debug('Node does not have linked file', node.path)
            return False
        for ds in self.doc.data.values():
            if ds.linked == lk:
                self.navigator.deleteData(ds)

        for key, ds in self.doc.available_data.items():
            if ds.linked == lk:
                del self.doc.available_data[key]

        self.model().refresh(True)

    @node
    def reloadFile(self, node=False, version=None):
        logging.debug('RELOADING', node.path, repr(version))
        linked = node.linked
        if not linked:
            logging.warning('Cannot reload unlinked dataset', node.path)
            return False
        if version is not None:
            # propagate new version information to all datasets
            for ds in self.doc.data.values():
                if ds.linked and ds.linked.params.filename==node.linked.params.filename:
                    ds.linked.params.version = version
            linked.params.version=version
        r = linked.reloadLinks(self.doc)
        self.doc.setModified()
        logging.debug('reloadLinks', r)

    @node
    def recalculate_metadata(self, node=False):
        iutils.with_waiting_mouse_cursor(lambda: self._recalculate_metadata(node))
        QtGui.QMessageBox.information(None,'Info', 'Metadata recalculated')

    def _recalculate_metadata(self, node):
        shared_file = SharedFile(node.linked.filename)
        shared_file.conf = node.get_configuration().root
        shared_file.run_scripts()


    def load_version(self, LF, version):
        # FIXME: VERSIONING!
        logging.debug('LOAD VERSION')
        LF.params.version = version
        LF.reloadLinks(self.doc)

        fl = self.model().files
        logging.debug('got linked files', self.model().files[:])

    def add_load(self, menu, node):
        """Add load/unload action"""
        self.act_load = menu.addAction(_('Load'), self.navigator.load)
        self.act_load.setCheckable(True)
        is_loaded = True
        if node.linked is None:
            self.act_load.setVisible(False)
        else:
            is_loaded = (node.ds is not False) and (len(node.ds) > 0)
            self.act_load.setChecked(is_loaded)
            if not is_loaded:
                menu.addAction(iutils.theme_icon('help-about'), _('Plot'), self.plot)
        return is_loaded

    @node
    def keep(self, node=False):
        """Inverts the 'keep' flag on the current dataset,
        causing it to be saved (or not) on the next file commit."""
        ds, node = self.dsnode(node)
        cur = getattr(ds, 'm_keep', False)
        ds.m_keep = not cur

    def add_keep(self, menu, node):
        temporary_disabled = True
        return temporary_disabled
        """Add on-file persistence action"""
        self.act_keep = menu.addAction(
            _('Saved on test file'), self.keep)
        self.act_keep.setCheckable(True)
        self.act_keep.setChecked(node.m_keep)

    @node
    def save_on_current_version(self, node=False):
        #FIXME: Find out local t dataset!
        proxy = getFileProxy(node.linked.filename, mode='a')
        prefix = node.linked.prefix
        try:
            proxy.save_data(node.ds.m_col, node.ds.data, self.model().doc.data[prefix + "t"].data)
        except Exception as e:
            message = "Impossible to save data.\n\n" + str(e)
            QtGui.QMessageBox.warning(None,'Error', message)
        proxy.close()

    @nodes
    def overwrite(self, nodes=[]):
        """Overwrite first selected dataset with second selected."""
        from misura.client import plugin
        p = plugin.OverwritePlugin(
            dst=nodes[0].path, src=nodes[1].path, delete=True)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.OverwritePlugin)
        self.mainwindow.showDialog(d)
        
    def activate_rule(self, node, act):
        line = '\n{}$'.format(node.path.split(':')[-1])
        rule = 'rule_'+rule_suffixes[act-1]
        if line in confdb[rule]:
            logging.warning('Rule already exists: {}\n{}'.format(line, confdb[rule]))
        else:
            confdb[rule]+=line
            logging.warning('Added rule:', rule, line, confdb[rule])
            
        
        # Remove any lower rule
        o = set(range(1, 5))
        o.remove(act)
        for n in o:
            logging.debug('REMOVING OTHER RULE', n)
            self.deactivate_rule(node, n)
        
        confdb._rule_dataset = False
        
        
    def deactivate_rule(self, node, act):
        line = '\n{}$'.format(node.path.split(':')[-1])
        rule = 'rule_'+rule_suffixes[act-1]
        txt = confdb[rule]
        if line in txt:
            confdb[rule] = txt.replace(line, '')
            logging.debug('Removing rule', rule, line, confdb[rule])
        else:
            logging.warning('Error removing load rule', rule, line)
            return False
        
        confdb._rule_dataset = False
        return True

    @node
    def change_rule(self, node=False, act=False):
        """Change current loading rule."""
        if not act:
            return False
        checked = self.act_rule[act-1].isChecked()
        
        if checked: 
            logging.debug('Activating rule', node, act)
            self.activate_rule(node, act)
        else:
            logging.debug('Deactivating rule', node, act)
            self.deactivate_rule(node, act)
            
        confdb.save()
        self.update_role_actions(node)

    def update_role_actions(self, node):
        # Find the highest matching rule
        all = confdb.rule_dataset(node.path, latest='all')
        if not all:
            return
        for r in all:
            self.act_rule[r[0] - 1].setChecked(True)
        # Resolve dependencies
        # Plot involves loading
        if self.act_rule[3].isChecked():
            self.act_rule[2].setChecked(True)
        # Loading involves listing
        if self.act_rule[2].isChecked():
            self.act_rule[1].setChecked(True)
        # Ignore disables load/plot
        if self.act_rule[0].isChecked():
            self.act_rule[2].setChecked(False)
            self.act_rule[3].setChecked(False)
        
        
        

    def add_rules(self, menu, node):
        """Add loading rules sub menu"""
        menu = menu.addMenu(_('Rules'))
        self.act_rule = []
        self.func_rule = []

        def gen(name, trname):
            f = functools.partial(self.change_rule, act=name)
            act = menu.addAction(trname, f)
            act.setCheckable(True)
            self.act_rule.append(act)
            self.func_rule.append(f)

        gen(1, _('Ignore'))
        gen(2, _('Available'))
        gen(3, _('Load'))
        gen(4, _('Plot'))
        
        self.update_role_actions(node)



    @node
    def configure(self, node):
        """Show node configuration panel"""
        path = node.path.split(':')[-1]
        #win = self.configuration_windows.get(path, False)
        #if win:
        #    win.show()
        #    return 
        cp = node.linked.conf
        if '/' in path:
            cp = cp.toPath(path)
        self.configure_proxy(cp, path)
        
    def configure_proxy(self, proxy, path=False):
        if not path:
            path = proxy['fullpath']
        win = conf.TreePanel(proxy, select=proxy)
        win.setWindowTitle('Configuration tree from: %s' % proxy['name'])
        win.show()
        # Keep a reference for Qt
        self.configuration_windows[path] = win     

    def add_configuration(self, menu, node):
        if node.linked and hasattr(node.linked, 'conf'):
            menu.addAction(iutils.theme_icon("details"), _('Details'), self.configure)
            
    def add_nodoc_menu(self, menu, proxy):
        menu.addAction(_('Configure'), functools.partial(self.configure_proxy, proxy))
        
    @node
    def add_versions_menu(self, node=False, menu=None):
        if not node:
            return False
        if not node.linked:
            return False
        proxy = self.doc.proxies.get(node.linked.params.filename, None)
        logging.debug('add_versions_menu', node, node.linked.params.filename, proxy)
        if proxy is not None:
            versions = VersionMenu(self.doc, proxy=proxy, parent=menu)
            if menu:
                menu.addMenu(versions)
            versions.versionChanged.connect(functools.partial(self.reloadFile, node))
            return versions
        logging.warning('Cannot create versions menu')
        return False

    def add_file_menu(self, menu, node):
        menu.addAction(iutils.theme_icon("add"), _('View'), self.viewFile)
        menu.addAction(_('Reload'), self.reloadFile)
        menu.addAction(_('Recalculate metadata'), self.recalculate_metadata)
        a = menu.addAction(iutils.theme_icon('edit-delete'), _('Close'), self.closeFile)
        self.versions = self.add_versions_menu(node, menu)
        self.add_configuration(menu, node)
        if len(self.data_tables):
            tab_menu = menu.addMenu('Tables')
            for tab_name, tab_window in self.data_tables.iteritems():
                if len(tab_name)>30:
                    tab_name = tab_name[:30] + '...'
                tab_menu.addAction(tab_name, tab_window.show)
        return True

    def add_group_menu(self, menu, node):
        self.add_configuration(menu, node)

    def add_sample_menu(self, menu, node):
        self.add_configuration(menu, node)
        menu.addAction(_('Delete'), self.navigator.deleteChildren)
        return True

    def add_dataset_menu(self, menu, node):
        menu.addSeparator()
        self.add_load(menu, node)
        self.add_keep(menu, node)
        menu.addAction(iutils.theme_icon('edit'), _('Edit (V)'), self.edit_dataset)
        menu.addAction(('Save on current version'), self.save_on_current_version)
        self.add_rules(menu, node)
        menu.addAction(_('Delete'), self.navigator.deleteData)
        return True

    def add_derived_dataset_menu(self, menu, node):
        self.add_keep(menu, node)
        menu.addAction(iutils.theme_icon('edit'), _('Edit (V)'), self.edit_dataset)
        menu.addAction(_('Delete'), self.navigator.deleteData)

    def create_table(self, header):
        tab_name = ', '.join(header)
        key = 'SummaryWidget:'+tab_name
        if self.navigator.show_widget_key(key):
            return
        
        from misura.client.fileui import SummaryWidget
        tab = SummaryWidget()#self.navigator)
        tab.set_doc(self.doc)
        tab.model().auto_load = False
        tab.model().set_loaded(header)
        
        tab.setWindowTitle('Table {} ({})'.format(len(self.data_tables), tab_name))
        self.navigator.show_widget(tab, key)
        # Keep another reference for nav menu
        self.data_tables[tab_name] = tab
        
    
    def export_csv(self, datasets):
        table_model_export(datasets, self.doc.get_column_func, None, self.navigator, 
                           self.doc.get_unit_func,
                           self.doc.get_verbose_func)

    def add_multiary_menu(self, menu, nodes):
        header = self.get_datasets_from_selection()
        nodes = [h[1] for h in header]
        header = [h[0] for h in header]
        if len(header):
            menu.addAction(_('Table from selection'), functools.partial(self.create_table, header))
            menu.addAction(_('Export to csv'), functools.partial(self.export_csv, header))
        menu.addAction(_('Delete selection'), self.navigator.deleteDatas)
        if len(nodes)==2:
            a = menu.addAction(_('Overwrite {} with {}').format(nodes[0].name(), nodes[1].name()), self.overwrite)
            a.setToolTip(_('{} will be overwritten by {}').format(nodes[0].path, nodes[1].path))
            #Qt5.1: a.setToolTipVisible(True)
            

from ..clientconf import confdb
class PlottingNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        if not node:
            return False
        if not node.ds:
            return False
        is_loaded = len(node.ds) > 0
        return is_loaded

    @node
    def thermalLegend(self, node=False):
        """Write thermal cycle onto a text label"""
        from misura.client import plugin
        p = plugin.ThermalCyclePlugin(test=node)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.ThermalCyclePlugin)
        self.mainwindow.showDialog(d)

    @node
    def intercept(self, node=False):
        """Intercept all curves derived/pertaining to the current object"""
        if isinstance(node, DatasetEntry):
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

    def add_plotted(self, menu, node, is_plotted=False):
        """Add plot/unplot action"""
        self.act_plot = menu.addAction(iutils.theme_icon('help-about'), _('Plot'), self.plot)
        self.act_plot.setCheckable(True)
        self.act_plot.setChecked(is_plotted)
        

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

    def find_style_row(self, path):
        idx = -1
        row = False
        for i, row in enumerate(confdb.rule_style.tab[1:]):
            if row[0]==path:
                logging.debug('Overwriting rule', idx, row)
                idx = i
                break
        return idx, row

    @node
    def save_style(self, node=False, curve=True, axis=True):
        """Save current curve color, style, marker and axis ranges and scale."""
        page = self.navigator.get_page().path
        plotpath = self.navigator.widget_path_for(node, prefix=page)
        if not len(plotpath) > 1:
            return False
        
        plot = self.doc.resolveFullWidgetPath(plotpath)
        
        path = node.path.split(':')[-1]+'$'
        
        style = ['', '', '', '', '']
        if axis and plot.parent.hasChild(plot.settings.yAxis):
            yaxis = plot.parent.getChild(plot.settings.yAxis)
            style[confdb.RULE_RANGE] = '{}:{}'.format(yaxis.settings.min, yaxis.settings.max)
            style[confdb.RULE_SCALE] = yaxis.settings.datascale
        if curve: 
            style[confdb.RULE_COLOR] = plot.settings.PlotLine.color
            style[confdb.RULE_LINE] = plot.settings.PlotLine.style
            style[confdb.RULE_MARKER] =  plot.settings.marker
        
        style =[path]+style
        
        idx, row = self.find_style_row(path)
        tab = confdb['rule_style']
        if idx<0:
            tab.append(style)
        else:
            tab[idx+1] = style
        
        confdb['rule_style'] = tab    
        logging.debug('Saving new style', tab)   
        confdb.save()
        confdb._rule_style = False
        
    @node
    def save_curve_style(self, node):
        return self.save_style(node, axis=False)

    @node
    def save_axis_style(self, node):
        return self.save_style(node, curve=False)

    @node
    def delete_style(self, node=False):
        """Delete style rule."""
        # TODO: delete_style
        path = node.path.split(':')[-1]+'$'
        idx, row= self.find_style_row(path)
        if idx<0:
            logging.warning('Could not find saved style rule', path)
            return False
        tab = confdb['rule_style']
        r = tab.pop(idx+1)
        logging.debug('Removed saved style rule', idx, r)
        confdb['rule_style'] = tab
        confdb._rule_style = False
        confdb.save()
        

    def add_styles(self, menu, node):
        """Styles sub menu"""
        plotpath = self.model().is_plotted(node.path)
        if not len(plotpath) > 0:
            return
        style_menu = menu.addMenu(_('Style'))

        wg = self.doc.resolveFullWidgetPath(plotpath[0])
        self.act_color = style_menu.addAction(
            _('Colorize'), self.colorize)
        self.act_color.setCheckable(True)
        
        act_save_style = style_menu.addAction(
            _('Save curve and axis style'), self.save_style)
        act_save_curve_style = style_menu.addAction(
            _('Save curve style'), self.save_curve_style)
        act_save_axis_style = style_menu.addAction(
            _('Save axis style'), self.save_axis_style)
        act_save_style.setCheckable(True)
        
        self.act_delete_style = style_menu.addAction(
            _('Delete style'), self.delete_style)
        
        if len(wg.settings.Color.points):
            self.act_color.setChecked(True)
        if confdb.rule_style(node.path):
            act_save_style.setChecked(True)

    def build_file_menu(self, menu, node):
        menu.addAction(_('Thermal Legend'), self.thermalLegend)
        menu.addAction(_('Intercept all curves'), self.intercept)
        return True

    def add_sample_menu(self, menu, node):
        menu.addAction(_('Intercept all curves'), self.intercept)
        menu.addAction(_('Delete'), self.navigator.deleteChildren)
        return True

    def add_dataset_menu(self, menu, node):
        menu.addSeparator()
        is_plotted = self.is_plotted(node) >0
        self.add_plotted(menu, node, is_plotted)
        if is_plotted:
            menu.addAction(_('Intercept this curve'), self.intercept)
            self.add_styles(menu, node)
        return True

    add_derived_dataset_menu = add_dataset_menu


    @nodes
    def synchronize(self, nodes=[]):
        from misura.client import plugin
        page = self.navigator.get_page().path
        paths = []
        for node in nodes:
            paths.append( self.navigator.widget_path_for(node, prefix=page) )
            

        sync_plugin = plugin.SynchroPlugin(*paths)

        dialog = PluginDialog(self.mainwindow,
                              self.doc,
                              sync_plugin,
                              plugin.SynchroPlugin)
        self.mainwindow.showDialog(dialog)

    def add_multiary_menu(self, menu, nodes):
        menu.addAction(_('Synchronize curves'), self.synchronize)


import veusz.document as document


class MathNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        if not node:
            return False
        if not node.ds:
            return False
        istime = node.path == 't' or node.path.endswith(':t')
        is_loaded = len(node.ds) > 0
        return (not istime) and is_loaded

    @node
    def smooth(self, node=False, dialog=True):
        """Call the SmoothDatasetPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)
        from misura.client import plugin
        out = node.path + '/sm'
        fields = dict(ds_in=node.path, ds_out=out, window=int(w))
        p = plugin.SmoothDatasetPlugin(**fields)
        if dialog:
            d = PluginDialog(
                self.mainwindow, self.doc, p, plugin.SmoothDatasetPlugin)
            self.mainwindow.showDialog(d)
        else:
            op = document.OperationDatasetPlugin(p, fields)
            self.doc.applyOperation(op)
        return out
    
    @node
    def smooth_no_dialog(self, node=False):
        if not node:
            return False
        return self.smooth(node, False)
        
    @node
    def smooth_and_plot(self, node=False):
        smooth_ds = self.smooth_no_dialog(node)
        plots = self.model().is_plotted(node.path)
        # Not plotted: add a new plot
        if not plots:
            # Remap children
            node.children
            n = node.root.traverse_path(smooth_ds)
            logging.debug('Plotting smoothed data', smooth_ds,n)
            self.plot(n)
            return
        # Already plotted: replace yData in all plots
        ops = []
        for path in plots:
            p = self.doc.resolveFullWidgetPath(path)
            op = document.OperationSettingSet(p.settings.get('yData'), smooth_ds)
            ops.append(op)
        self.doc.applyOperation(document.OperationMultiple(ops, 'SmoothAndPlot'))
        
    @node
    def bandpass(self, node=False):
        """Call the BandPassPlugin on the current node"""
        ds, node = self.dsnode(node)
        ds_t = self.xnames(node, '/time')[0]
        from misura.client import plugin
        p = plugin.BandPassPlugin(
            ds_in=node.path, ds_t=ds_t, ds_out=node.m_name + '/bp')
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.BandPassPlugin)
        self.mainwindow.showDialog(d)

    @node
    def coefficient(self, node=False):
        """Call the CoefficientPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)
        ds_x = self.xnames(node, '/temperature')[0]
        ini = getattr(ds, 'm_initialDimension', None)
        if not ini: 
            ini = 0.
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
            ds_y=node.path, ds_x=ds_x, ds_out=node.m_name + '/der', smooth=w)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.DeriveDatasetPlugin)
        self.mainwindow.showDialog(d)


    def add_dataset_menu(self, menu, node):
        menu.addSeparator()
        menu.addAction(_('Smooth (Alt+S)'), self.smooth)
        menu.addAction(iutils.theme_icon('smooth'), _('Smooth+plot (S)'), self.smooth_and_plot)
        
        menu.addAction(_('BandPass'), self.bandpass)
        menu.addAction(_('Derivatives'), self.derive)
        menu.addAction(_('Linear Coefficient'), self.coefficient)
        
    def create_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ALT+QtCore.Qt.Key_S), 
                        self.navigator, 
                        self.smooth_no_dialog, 
                        context=QtCore.Qt.WidgetWithChildrenShortcut)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_S), 
                        self.navigator, 
                        self.smooth_and_plot,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)
        
    add_derived_dataset_menu = add_dataset_menu

    @nodes
    def correct(self, nodes=[]):
        """Call the CurveOperationPlugin on the current nodes"""
        ds0, node0 = self.dsnode(nodes[0])
        T0 = node0.linked.prefix + 'kiln/T'
        ds1, node1 = self.dsnode(nodes[1])
        T1 = node1.linked.prefix + 'kiln/T'
        from misura.client import plugin
        p = plugin.CurveOperationPlugin(
            ax=T0, ay=node0.path, bx=T1, by=node1.path, ds_out=node0.path+'/corr')
        # TODO: TC comparison?
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.CurveOperationPlugin)
        self.mainwindow.showDialog(d)
        
    

    def add_multiary_menu(self, menu, nodes):
        datasets = self.get_datasets_from_selection()
        nodes = [d[1] for d in datasets]
        if len(datasets)==2:
            menu.addAction(_('Correct'), functools.partial(self.correct, nodes))
        if len(datasets):
            menu.addAction(_('Smooth all'), functools.partial(self.iternodes, nodes, self.smooth, dialog=False))
            menu.addAction(_('Smooth+plot all'), functools.partial(self.iternodes, nodes, self.smooth_and_plot))


class MeasurementUnitsNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        if not node:
            return False
        if not node.ds:
            return False
        return len(node.ds) > 0

    @node
    def setInitialDimension(self, node=False):
        """Invoke the initial dimension plugin on the current entry"""
        logging.debug('Searching dataset name', node, node.path)
        n = self.doc.datasetName(node.ds)
        ini = getattr(node.ds, 'm_initialDimension', False)
        if not ini:
            ini = 100.
        xname = self.xnames(node)[0]
        logging.debug('Invoking InitialDimensionPlugin', n, ini)
        from misura.client import plugin
        p = plugin.InitialDimensionPlugin(ds=n, ini=ini, ds_x = xname)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.InitialDimensionPlugin)
        self.mainwindow.showDialog(d)

    @node
    def convertPercent(self, node=False):
        """Invoke the percentage plugin on the current entry"""
        n = self.doc.datasetName(node.ds)
        from misura.client import plugin
        p = plugin.PercentPlugin(ds=n, propagate=True)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.PercentPlugin)
        self.mainwindow.showDialog(d)

    @node
    def set_unit(self, node=False, convert=False):
        logging.debug('set_unit:', node, node.unit, convert)
        if node.unit == convert or not convert or not node.unit:
            logging.debug('set_unit: Nothing to do')
            return
        n = self.doc.datasetName(node.ds)
        from misura.client import plugin
        p = plugin.UnitsConverterTool(ds=n, convert=convert, propagate=True)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.UnitsConverterTool)
        self.mainwindow.showDialog(d)

    def add_percent(self, menu, node):
        """Add percentage conversion action"""
        self.act_percent = menu.addAction(
            _('Set Initial Dimension'), self.setInitialDimension)
        self.act_percent = menu.addAction(iutils.theme_icon('percent'),
            _('Percentage'), self.convertPercent)
        self.act_percent.setCheckable(True)
        self.act_percent.setChecked(node.m_percent)

    def add_unit(self, menu, node):
        """Add measurement unit conversion menu"""
        self.units = {}
        u = node.unit
        if not u:
            return
        un = menu.addMenu(_('Units'))
        kgroup, f, p = units.get_unit_info(u, units.from_base)
        same = units.from_base.get(kgroup, {u: lambda v: v}).keys()
        logging.debug( kgroup, same)
        for u1 in same:
            p = functools.partial(self.set_unit, convert=u1)
            act = un.addAction(_(u1), p)
            act.setCheckable(True)
            if u1 == u:
                act.setChecked(True)
            # Keep reference
            self.units[u1] = (act, p)

    def add_dataset_menu(self, menu, node):
        menu.addSeparator()
        if not node.path.endswith(':t'):
            self.add_percent(menu, node)
        self.add_unit(menu, node)


navigator_domains += PlottingNavigatorDomain, MathNavigatorDomain, MeasurementUnitsNavigatorDomain, DataNavigatorDomain
