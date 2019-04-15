#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Custom Misura plotting facilities."""
from veusz import document
from misura.canon.plugin import default_plot_plugins
from misura.client.plugin import DefaultPlotPlugin, ArrangePlugin

class SummaryPlotPlugin(DefaultPlotPlugin):
    """Summary Plot from a Flash test"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'Make default Summary Plot')
    # unique name for plugin
    name = 'Flash default plot'
    # name to appear on status tool bar
    description_short = 'Default plot for Flash tests'
    # text to appear in dialog box
    description_full = 'Default plot for Flash tests'
    
    def apply(self, cmd, fields):
        self.doc = cmd.document
        # Delete the time page
        if len(self.doc.basewidget.children)==2:
            t = self.doc.basewidget.getChild('time')
            if t:
                self.doc.applyOperation(document.OperationWidgetDelete(t))
        # Remove the time target
        graphs = fields.get('graphs', ['/temperature/temp'])
        if '/time/time' in graphs:
            graphs.remove('/time/time')
        fields['graphs'] = graphs
        
        r = DefaultPlotPlugin.apply(self, cmd, fields)
        for g in self.created:
            p = ArrangePlugin()
            p.apply(self.cmd, {'currentwidget': g,
                                     'axis': 'Line Style', 
                                     'path': 'Line Color', 'space': False})

        return r
  
default_plot_plugins['flash'] = SummaryPlotPlugin