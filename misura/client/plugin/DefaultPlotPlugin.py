#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Custom Misura plotting facilities."""
import re

import veusz.plugins as plugins
from veusz import document
from misura.canon.option import namingConvention
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from .. import axis_selection
from PlotPlugin import PlotDatasetPlugin
from MakeDefaultDoc import MakeDefaultDoc
from . import utils

class DefaultPlotPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Default Plot from a list of Misura datasets."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Make a default plot from a list of datasets')
    # unique name for plugin
    name = 'Misura default plot'
    # name to appear on status tool bar
    description_short = 'Default plot for Misura datasets'
    # text to appear in dialog box
    description_full = 'Default plot for Misura datasets'

    def __init__(self, dsn=[], rule='', graphs = ['/time/time', '/temperature/temp'], title=''):
        """Make list of fields."""

        self.fields = [
            plugins.FieldDatasetMulti("dsn", 'Dataset names', default = dsn),
            plugins.FieldText("rule", 'Plotting rule', default=rule),
            plugins.FieldTextMulti("graphs", 'Target graphs', default=graphs),
            plugins.FieldText("title", 'Plot title', default=title),
        ]
        self.created = []
        
    def get_time_datasets(self, names, graph):
        x = []
        y = []
        for ds in names:
            prefix = ''
            if ':' in ds:
                prefix, ds1 = ds.split(':')
                prefix += ':'
            timeds = axis_selection.get_best_x_for(
                ds, prefix, self.doc.data, graph)
            if timeds:
                y.append(ds)
                x.append(timeds)
            else:
                print 'NO TIMEDS FOUND FOR', ds     
        return x, y
                
    def get_temperature_datasets(self, names, graph):
        x = []
        y = []
        for ds in names:
            if axis_selection.is_temperature(ds):
                continue
            prefix = ''
            if ':' in ds:
                prefix, ds1 = ds.split(':')
                prefix += ':'        
            ds_temperature = axis_selection.get_best_x_for(
                ds, prefix, self.doc.data, graph)
            if ds_temperature:
                x.append(ds_temperature)
                y.append(ds)  
        return x, y      
        
    def create_graph(self, graph):
        """Create page and graph if missing"""
        try:
            self.doc.resolveFullWidgetPath(graph)
            print 'GRAPH OK', graph
            return False
        except:
            pass
        print 'GRAPH MISSING', graph
        vgraph = graph.split('/')
        page = vgraph[1][:-2]
        has_grid = vgraph[-2] == 'grid'
        print 'MakeDefaultPlot', page, has_grid, graph
        istime = graph.endswith('/time') or graph.endswith('_time')
        istemp = graph.endswith('/temp') or graph.endswith('_temp')
        self.ops.append(
            document.OperationToolsPlugin(MakeDefaultDoc(), 
                {'title': self.fields.get('title', ''), 'page': page,
                 'time': istime , 
                 'temp': istemp,
                 'grid': has_grid})
            )
        self.apply_ops()
        logging.debug('Done create_graph', graph)
        return True
          
    def plot_on_graph(self, names, graph):
        print 'plot_on_graph', graph, len(names)
        self.create_graph(graph)
        if graph.endswith('/temp'):
            x, y = self.get_temperature_datasets(names, graph)
        elif graph.endswith('/time'):
            x, y = self.get_time_datasets(names, graph)      
        
        result = PlotDatasetPlugin().apply(
            self.cmd, {'x': x, 'y': y, 'currentwidget': graph})
        print 'Done plot_on_graph', graph
        self.created.append(graph)
        return result
        
    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.cmd = cmd
        self.doc = cmd.document
        self.fields = fields
        dsn = fields['dsn']
        names = []
        rp = fields['rule'].replace('\n', '|')
        if len(rp) > 0:
            rp = re.compile(rp)
        else:
            rp = False
            
        for ds in dsn:
            ds1 = ds
            if ':' in ds1:
                ds1 = ds1.split(':')[1]
            var = namingConvention(ds1)[0]
            logging.debug('%s %s %s', 'Checking', ds, var)
            if rp and rp.search(ds1):
                names.append(ds)
                
        if not len(names):
            print 'NOTHING TO PLOT', names, fields['rule'], dsn, rp
            return False

        names = sorted(names)
        logging.debug('%s %s', "VARS", names)
        
        result={}
        graphs = fields.get('graphs',['/time/time', '/temperature/temp'])
        for graph in graphs:
            r = self.plot_on_graph(names, graph)
            result.update(r)
        return result
