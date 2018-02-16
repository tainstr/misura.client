#!/usr/bin/pythonthin
# -*- coding: utf-8 -*-
"""Arrange curves and axes"""
from collections import defaultdict
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import veusz.utils
from misura.client.iutils import get_plotted_tree
from misura.client.colors import colorize, colorLevels
import utils
from misura.client.clientconf import confdb
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
    '#000000',  # black
    '#c10020',  # vivid red
    '#00538a',  # strong blue
    '#007d34',  # vivid green
    '#ff6800',  # vivid orange
    '#803e75',  # strong purple
    '#a6bdd7',  # very light blue

    '#f6768e',  # strong purplish pink
    '#53377a',  # strong violet
    '#ff7a5c',  # strong yellowish pink

    '#ff8e00',  # vivid orange yellow
    '#b32851',  # strong purplish red
    '#f4c800',  # vivid greenish yellow
    '#7f180d',  # strong reddish brown
    '#93aa00',  # vivid yellowish green
    '#593315',  # deep yellowish brown
    '#f13a13',  # vivid reddish orange
    '#232c16',  # dark olive green
    '#ffb300',  # vivid yellow

    '#cea262',  # grayish yellow
    '#817066',  # medium gray
]


def find_unused_color(used):
    idx = 0
    color = kelly_colors[idx]
    while color in used:
        logging.debug('color is used', color)
        idx += 1
        if idx >= len(kelly_colors):
            logging.error('Exausted free colors!')
            color = '#000000'
        else:
            color = kelly_colors[idx]
    logging.debug('found color', color)
    return color


persistent_styles = ('PlotLine/color', 'MarkerFill/color', 'MarkerLine/color', 
                     'PlotLine/width', 'PlotLine/hide',
                     'PlotLine/style', 'marker', 'markerSize', 'color', 'thinfactor')


def save_plot_style_in_dataset_attr(plot, cmd):
    """Save plot style information into dataset attributes upon plot creation/destruction"""
    dsname = plot.settings['yData']
    pp = plot.parent.path
    for attr in persistent_styles:
        val = plot.settings.getFromPath(attr.split('/')).get()
        cmd.SetDataAttr(dsname, pp +'|'+attr, val)
    # Saving related graph
    cmd.SetDataAttr(dsname, pp+':ax', plot.settings['yAxis'])

def get_plot_style_from_dataset_attr(plot, ds):
    """Read plot style attributes from dataset ds"""
    props = {}
    pp = plot.parent.path
    for attr in persistent_styles:
        val = ds.attr.get(pp+'|'+attr, None)
        if val is None:
            continue
        props[attr] = val
    return props


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

    def __init__(self, axis='Line Color', path='Line Style', space=False):
        """Make list of fields."""
        if not axis:
            axis = confdb['rule_autoformat']
            path = 'Line Color' if axis=='Line Style' else 'Line Style'
        self.fields = [
            plugins.FieldCombo(
                "axis", descr="Mark curves sharing same axis by:", items=defvars.keys(), default=axis),
            plugins.FieldCombo(
                "path", descr="Mark curves sharing same path by:", items=defvars.keys(), default=path),
            plugins.FieldBool(
                "space", descr="Auto axis positioning:", default=space)
        ]

    def arrange_axes(self, tree, graph):
        """Adjust Axes colors and positions"""
        axes = sorted(tree['axis'].keys())
        axcolors = {}
        axstyles = {}
        axmarkers = {}
        for idx, axp in enumerate(axes[:]):
            ax = self.doc.resolveFullWidgetPath(axp)
            if not axp.startswith(graph) or ax.settings.direction != 'vertical':
                axes.remove(axp)
                continue
            # Normalize colors to their html #code
            axcolors[ax.name] = str(QtGui.QColor(
                ax.settings.Line.color).name())
            axstyles[ax.name] = lineStyles[idx]
            axmarkers = veusz.utils.MarkerCodes[idx]
            
        dataset_ax_colors = defaultdict(set)
        dataset_colors = set()
        for ds in self.doc.data.values():
            c = ds.attr.get(graph+'|PlotLine/color', None)
            if c is None:
                continue
            axpath = ds.attr.get(graph+':ax', None)
            if axpath is not None:
                dataset_ax_colors[axpath].add(c)
                dataset_colors.add(c)
        
        # Total axes for repositioning
        if len(axes) > 1:
            tot = 1. / (len(axes) - 1)
        else:
            tot = 0

        for idx, axpath in enumerate(axes):
            props = {}
            ax = self.doc.resolveFullWidgetPath(axpath)
            other_ax_colors = axcolors.copy()
            other_ax_colors.pop(ax.name)
            used = other_ax_colors.values()
            used += list(dataset_colors-dataset_ax_colors[axpath])
            color = '#000000'
            dscolor = dataset_ax_colors[ax.name]
            if self.fields['axis'] == 'Line Color':
                if hasattr(ax, 'm_auto'):
                    color = axcolors[ax.name]
                    logging.debug('m_auto override', color)
                elif len(dscolor):
                    color = list(dscolor)[0]
                elif len(axes) > 1:
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

        return axes, axcolors, axstyles, axmarkers

    def arrange_curve(self, plotpath, tree, axes, axcolors, axstyles, axmarkers, 
                      var, m_var, LR, LG, LB, unused_formatting_opt):
        """Set colors according to axes"""
        obj = self.doc.resolveFullWidgetPath(plotpath)
        # Get y dataset
        y = obj.settings['yData']
        if not self.doc.data.has_key(y):
            logging.error(
                'No y dataset found - skipping invisible curve', plotpath, y)
            return False

        # Flag passed by PlotPlugin to operate exclusively on currently plotted
        # curves
        props = {}
        plotted_dataset_names = self.fields.get('plotted_dataset_names', [])
        if y in plotted_dataset_names:
            if self.fields['axis'] == 'Line Color':
                color = axcolors[obj.settings.yAxis]
                props = {'color': color, 
                         'PlotLine/color': color,
                         'MarkerFill/color': color,
                         'MarkerLine/color': color}
            elif self.fields['axis'] == 'Line Style':
                props = {'PlotLine/style': axstyles[obj.settings.yAxis]}
            elif self.fields['axis'] == 'Point Marker':
                props = {'marker': axmarkers[obj.settings.yAxis]}

        # Set plot line or marker according to ax index
        yax = obj.parent.getChild(obj.settings.yAxis)
        if yax is None:
            return False
        iax = axes.index(yax.path)

        if self.fields['axis'] == 'Point Marker':
            props['PlotLine/style'] = 'solid'
            props['marker'] = veusz.utils.MarkerCodes[iax]
        elif self.fields['axis'] == 'Line Style':
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
            # FIXME: remove this! should inherit somehow.
            outvar = colorize(idx, LR, LG, LB)
        props[var] = outvar

        # Update with any property saved in dataset attr
        props.update(get_plot_style_from_dataset_attr(obj, self.doc.data[y]))
        
        self.dict_toset(obj, props, preserve=True)
        return obj

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
        if not 'axis' in fields:
            fields['axis'] = confdb['rule_autoformat']
        if not 'path' in fields:
            fields['path'] = 'Line Color' if fields['axis']=='Line Style' else 'Line Style'
        if fields['axis'] == fields['path']:
            raise plugins.ToolsPluginException(
                'You must choose different markers for Axis and Path.')

        unused_formatting_opt = set(
            defvars.keys()) - set([fields['path'], fields['axis']])
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
        axes, axcolors, axstyles, axmarkers = self.arrange_axes(tree, graph)
        # Set plot colors based on axis colors
        var, m_var, defvar = defvars[fields['axis']]
        LR, LG, LB = colorLevels(len(smps))
        plots = []
        for plotpath in tree['plot']:
            plot = self.arrange_curve(
                plotpath, tree, axes, axcolors, axstyles, axmarkers, 
                var, m_var, LR, LG, LB, unused_formatting_opt)
            
            plots.append(plot)
        self.apply_ops()
        
        for plot in plots:
            save_plot_style_in_dataset_attr(plot, self.cmd)


plugins.toolspluginregistry.append(ArrangePlugin)
