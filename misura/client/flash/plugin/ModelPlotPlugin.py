#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Custom Misura plotting facilities."""
from traceback import format_exc

from veusz import document

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.client.plugin.DefaultPlotPlugin import DefaultPlotPlugin 
from misura.client.plugin import PlotDatasetPlugin

from misura.client.plugin import utils

class ModelPlotPlugin(DefaultPlotPlugin):

    """Default Model Plot from a list of Misura datasets and a node."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'Make a default plot for a model')
    # unique name for plugin
    name = 'Flash model default plot'
    # name to appear on status tool bar
    description_short = 'Default plot for Flash models'
    # text to appear in dialog box
    description_full = 'Default plot for Flash models'      
        
    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        # Load datasets
        self.doc = cmd.document
        node = fields['node']
        node = self.doc.model.tree.traverse(node.path)
        sub0 = node.parent.path.split('/')
        theory = '/'.join(sub0+[node.name(),'theory'])
        residuals = '/'.join(sub0+[node.name(),'residuals'])
        t = '/'.join(sub0+[node.name()+'_t'])
        t_dataset = self.doc.get_cache(t, add_to_doc=True)
        if t_dataset is False:
            logging.error('Could not find dataset', t)
            t = theory+'_t'
            t_dataset = self.doc.get_cache(t, add_to_doc=True)
            if t_dataset is False:
                logging.error('Could not find dataset', t)
                return True
            t = residuals+'_t'
            t_dataset = self.doc.get_cache(t, add_to_doc=True)
            if t_dataset is False:
                logging.error('Could not find dataset', t)
                return True
            
        # Create default plot
        result = DefaultPlotPlugin.apply(self, cmd, fields)
        if not result:
            return result
        
        # Update time scale     
        t_max = float(max(t_dataset.data))*1.05
        t_min = -t_max/20.
        page = '/{}'.format(node.path.replace('/', '_'))
        t_ax = page + '_t/grid/time/x'
        ax_obj = self.doc.resolveFullWidgetPath(t_ax)
        self.toset(ax_obj, 'max', t_max)
        self.toset(ax_obj, 'min', t_min)
         
        yranges = self.fields.get('yranges', False)
        if yranges:
            self.set_ranges(page + '_t/grid/time', 'ax:Signal', yranges) 
        
        g = utils.searchFirstOccurrence(ax_obj, 'graph', -1)
        theory_plot = False
        for wg in g.children:
            if wg.typename != 'xy':
                continue
            dsn = wg.settings.yData
            if dsn != theory:
                continue
            theory_plot = wg
            break
        if theory_plot is not False:
            color = 'blue' 
            props = {'PlotLine/color': color,
                    'PlotLine/width': '2pt',
                    'MarkerFill/color': color,
                    'MarkerLine/color': color}
            for k,v in props.iteritems():
                self.toset(theory_plot, k, v)
        
        # Adjust the grid
        self.toset(g.parent, 'columns', 1)
        # Add the residuals graph, if missing
        if 'residuals_time' not in [w.name for w in g.parent.children]:
            logging.debug('Creating residuals graph')
            self.ops.append(
                (document.OperationWidgetAdd(g.parent, 'graph', name='residuals_time')))
        else:
            logging.debug('Residuals graph was found', [w.name for w in g.parent.children])
        self.apply_ops('Adjusting model plot')
        # Zero-out margins
        g.parent.actionZeroMargins()
            
        residuals_plot = page + '_t/grid/residuals_time'
        p = PlotDatasetPlugin()
        curves = p.apply(self.cmd, {
                    'x': [t], 
                    'y': [residuals], 
                    'currentwidget': residuals_plot})
        residuals_plot = g.parent.getChild('residuals_time')
        curve = residuals_plot.getChild(curves.values()[0])
        self.toset(curve, 'marker', u'circle')
        self.toset(curve, 'markerSize', u'1pt')
        self.toset(curve, 'PlotLine/hide', True)
        N=len(self.doc.get_cache(residuals) or [])
        self.toset(curve, 'thinfactor', max((1,int(N/2500.))))
        
        self.toset(ax_obj, 'match', '../residuals_time/x')
        
        #FIXME: why is there an y ax which needs to be removed...?
        residuals_xax = residuals_plot.getChild('x')
        try:
            y = residuals_xax.parent.getChild('y')
            self.ops.append(
                            (document.OperationWidgetDelete(y))
                             )
        except:
            logging.debug('While deleting empty y axis', format_exc())
            

            
        self.apply_ops()
        
        return result
