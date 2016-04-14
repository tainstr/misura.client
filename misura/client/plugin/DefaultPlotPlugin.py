#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Custom Misura plotting facilities."""
import re

import veusz.plugins as plugins
from misura.client import iutils
from misura.canon.logger import Log as logging
from .. import axis_selection
from PlotPlugin import PlotDatasetPlugin


class DefaultPlotPlugin(plugins.ToolsPlugin):

    """Default Plot from a list of Misura datasets."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Make a default plot from a list of datasets')
    # unique name for plugin
    name = 'Misura default plot'
    # name to appear on status tool bar
    description_short = 'Default plot for Misura datasets'
    # text to appear in dialog box
    description_full = 'Default plot for Misura datasets'

    def __init__(self, dsn=[], rule='', graphs = ['/time/time', '/temperature/temp']):
        """Make list of fields."""

        self.fields = [
            plugins.FieldDatasetMulti("dsn", 'Dataset names'),
            plugins.FieldText("rule", 'Plotting rule', default=rule),
            plugins.FieldTextMulti("graphs", 'Target graphs', default=graphs),
        ]
        
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
          
    def plot_on_graph(self, names, graph):
        print 'plot_on_graph', graph, len(names)
        if graph.endswith('/temp'):
            x, y = self.get_temperature_datasets(names, graph)
        elif graph.endswith('/time'):
            x, y = self.get_time_datasets(names, graph)      
        
        result = PlotDatasetPlugin().apply(
            self.cmd, {'x': x, 'y': y, 'currentwidget': graph})
        
        return result
        
    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.cmd = cmd
        self.doc = cmd.document
        
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
            var = iutils.namingConvention(ds1)[0]
            logging.debug('%s %s %s', 'Checking', ds, var)
            if rp and rp.search(ds1):
                names.append(ds)

        names = sorted(names)
        logging.debug('%s %s', "VARS", vars)
        
        result={}
        graphs = fields.get('graphs',['/time/time', '/temperature/temp'])
        for graph in graphs:
            r = self.plot_on_graph(names, graph)
            result.update(r)
        return result
