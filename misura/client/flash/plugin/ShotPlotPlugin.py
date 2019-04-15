#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Custom Misura plotting facilities."""
from veusz import document
from misura.canon.plugin import default_plot_plugins
from misura.client.plugin import DefaultPlotPlugin, ArrangePlugin

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)


class ShotPlotPlugin(DefaultPlotPlugin):
    """Shot Plot from a Flash test"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'Make default Shot Plot')
    # unique name for plugin
    name = 'Flash Shot default plot'
    # name to appear on status tool bar
    description_short = 'Default plot for Flash Shot'
    # text to appear in dialog box
    description_full = 'Default plot for Flash Shot'
    
    
    def apply(self, *a, **kw):
        r = DefaultPlotPlugin.apply(self, *a, **kw)
        xranges = self.fields.get('xranges', False)
        yranges = self.fields.get('yranges', False)
        for g in self.created:
            op = document.OperationToolsPlugin(ArrangePlugin(), 
                                    {'currentwidget': g,
                                     'axis': 'Line Style', 
                                     'path': 'Line Color', 'space': False})
            self.ops.append(op)
            if xranges:
                self.set_ranges(g, 'x', xranges)
                    
            if yranges:
                self.set_ranges(g, 'ax:Signal', yranges)             
                    
        self.apply_ops()
            
        return r
  
#default_plot_plugins['flash'] = ShotPlotPlugin