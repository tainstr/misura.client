#!/usr/bin/pythonthin
# -*- coding: utf-8 -*-
"""Arrange curves and axes"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import veusz.utils
from misura.client.iutils import get_plotted_tree
from misura.client.colors import colorize, colorLevels
import utils

from PyQt4 import QtGui

lineStyles = ['solid', 'dashed', 'dotted', 'dash-dot',
              'dash-dot-dot', 'dotted-fine', 'dashed-fine', 'dash-dot-fine',
              'dot1', 'dot2', 'dot3', 'dot4', 'dash1', 'dash2', 'dash3', 'dash4',
              'dash5', 'dashdot1', 'dashdot2', 'dashdot3']

defvars = {'Line Style': ('PlotLine/style', 'm_style', 'solid'),
           'Line Color': ('PlotLine/color', 'm_color', '#000000'),
           'Point Marker': ('marker', 'm_marker', 'none')
           }
# http://stackoverflow.com/a/4382138/1645874
kelly_colors = [
    '#000000', # black
    '#c10020', # vivid red
    '#00538a', # strong blue
    '#007d34', # vivid green
    '#ff6800', # vivid orange
    '#803e75', # strong purple
    '#a6bdd7', # very light blue
    
    '#f6768e', # strong purplish pink
    '#53377a', # strong violet
    '#ff7a5c', # strong yellowish pink
    
    '#ff8e00', # vivid orange yellow
    '#b32851', # strong purplish red
    '#f4c800', # vivid greenish yellow
    '#7f180d', # strong reddish brown
    '#93aa00', # vivid yellowish green
    '#593315', # deep yellowish brown
    '#f13a13', # vivid reddish orange
    '#232c16', # dark olive green
    '#ffb300', # vivid yellow
    
    '#cea262', # grayish yellow
    '#817066', # medium gray
    ]

def find_unused_color(used):
    idx = 0
    color = kelly_colors[idx]
    while color in used:            
        logging.debug('color is used', color)
        idx += 1
        if idx>=len(kelly_colors):
            logging.error('Exausted free colors!')
            color = '#000000'
        else:
            color = kelly_colors[idx]
    logging.debug('found color', color)
    return color

class ArrangePlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Arrange Y Axes and curve colors and marker styles following Misura samples grouping."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Arrange Axes And Colors')
    # unique name for plugin
    name = 'Arrange'
    # name to appear on status tool bar
    description_short = 'Arrange Axes and Color Curves'
    # text to appear in dialog box
    description_full = 'Arrange Y Axes and curve colors and marker styles following Misura samples grouping.'
    preserve = True

    def __init__(self, dataset='Line Color', sample='Line Style', space=False):
        """Make list of fields."""

        self.fields = [
            plugins.FieldCombo(
                "dataset", descr="Datasets marking mode:", items=defvars.keys(), default=dataset),
            plugins.FieldCombo(
                "sample", descr="Samples marking mode:", items=defvars.keys(), default=sample),
            plugins.FieldBool(
                "space", descr="Axis positioning:", default=space)
        ]

    def arrange_axes(self, tree, graph):
        """Adjust Axes colors and positions"""
        axes = sorted(tree['axis'].keys())
        axcolors = {}
        for axp in axes[:]:
            ax = self.doc.resolveFullWidgetPath(axp)
            if not axp.startswith(graph) or ax.settings.direction != 'vertical':
                axes.remove(axp)
            # Normalize colors to their html #code
            axcolors[ax.name] = str(QtGui.QColor(ax.settings.Line.color).name())
            
        # Total axes for repositioning
        if len(axes) > 1:
            tot = 1. / (len(axes) - 1)
        else:
            tot = 0
        
        for idx, axpath in enumerate(axes):
            ax = self.doc.resolveFullWidgetPath(axpath)
            other_ax_colors = axcolors.copy()
            other_ax_colors.pop(ax.name)
            used = other_ax_colors.values()
            
            color = '#000000'
            if self.fields['dataset'] == 'Line Color':
                if hasattr(ax, 'm_auto'):
                    color = axcolors[ax.name]
                    logging.debug('m_auto override', color)
                elif len(axes)>1:
                    # Generate html color for this idx
                    color = find_unused_color(used)

            axcolors[ax.name] = color
            props = {'Line/color': color,
                     'Label/color': color,
                     'TickLabels/color': color,
                     'MajorTicks/color': color,
                     'MinorTicks/color': color}

            # Reposition
            if self.fields['space']:
                props['otherPosition'] = idx * tot

            self.dict_toset(ax, props, preserve=True)

        return axes, axcolors

    def arrange_curve(self, plotpath, tree, axes, axcolors, var, m_var, LR, LG, LB, unused_formatting_opt):
        """Set colors according to axes"""
        obj = self.doc.resolveFullWidgetPath(plotpath)
        # Get y dataset
        y = obj.settings['yData']
        if not self.doc.data.has_key(y):
            logging.error('No y dataset found - skipping invisible curve', plotpath, y)
            return False
        
        # Flag passed by PlotPlugin to operate exclusively on currently plotted curves
        plotted_dataset_names = self.fields.get('plotted_dataset_names', False)
        
        if not plotted_dataset_names or y in plotted_dataset_names:
            color = axcolors[obj.settings.yAxis]
            props = {'PlotLine/color': color,
                     'MarkerFill/color': color,
                     'MarkerLine/color': color}
        else:
            props = {}

        # Set plot line or marker according to ax index
        yax = obj.parent.getChild(obj.settings.yAxis)
        if yax is None:
            return False
        iax = axes.index(yax.path)

        if self.fields['dataset'] == 'Point Marker':
            props['PlotLine/style'] = 'solid'
            props['marker'] = veusz.utils.MarkerCodes[iax]
        elif self.fields['dataset'] == 'Line Style':
            props['PlotLine/style'] = lineStyles[iax]
        
        # Set the unused style component to default
        #uvar, um_var, udefvar = defvars[unused_formatting_opt]
        #props[uvar] = udefvar

        # Secondary style value
        ax_datasets = tree['axis'][yax.path]
        if y in ax_datasets:
            idx = ax_datasets.index(y)
        else:
            idx = len(ax_datasets)
        if m_var == 'm_marker':
            outvar = veusz.utils.MarkerCodes[idx]
        elif m_var == 'm_style':
            outvar = lineStyles[idx]
        elif m_var == 'm_color':
            #FIXME: remove this! should inherit somehow.
            outvar = colorize(idx, LR, LG, LB)
        props[var] = outvar

        self.dict_toset(obj, props, preserve = True)
        return True

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        logging.debug('ArrangePlugin.apply')
        self.ops = []
        self.cmd = cmd
        self.doc = cmd.document
        self.fields = fields
        if fields['sample'] == fields['dataset']:
            raise plugins.ToolsPluginException(
                'You must choose different markers for Datasets and Samples.')

        unused_formatting_opt = set(
            defvars.keys()) - set([fields['sample'], fields['dataset']])
        unused_formatting_opt = list(unused_formatting_opt)[0]

        # Search for the graph widget
        gobj = self.doc.resolveFullWidgetPath(fields['currentwidget'])
        gobj = utils.searchFirstOccurrence(gobj, 'graph')
        if gobj is None or gobj.typename != 'graph':
            raise plugins.ToolsPluginException(
                'You should run this tool on a graph')

        graph = gobj.path
        tree = get_plotted_tree(gobj)
        smps = tree['sample']

        # Ax Positioning
        axes, axcolors = self.arrange_axes(tree, graph)
        # Set plot colors based on axis colors
        var, m_var, defvar = defvars[fields['sample']]
        LR, LG, LB = colorLevels(len(smps))
        for plotpath in tree['plot']:
            self.arrange_curve(
                plotpath, tree, axes, axcolors, var, m_var, LR, LG, LB, unused_formatting_opt)

        self.apply_ops()

plugins.toolspluginregistry.append(ArrangePlugin)
