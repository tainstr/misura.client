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
from random import choice
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
    'black',  # black
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


def find_unused(u, group):
    for s in group:
        if s not in u:
            logging.debug('found style', s)
            return s
        logging.debug('style is used', s)
    logging.debug('exausted free styles', s)
    return choice(group)



persistent_styles = ('PlotLine/color', 'MarkerFill/color', 'MarkerLine/color', 
                     'PlotLine/width', 'PlotLine/hide',
                     'PlotLine/style', 'marker', 'markerSize', 'color', 'thinfactor',
                     'key')


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

def select_ax_value(axgroup, ax, dsgroup, dsaxgroup, available, name):
    other= axgroup.copy()
    other.pop(ax.name)
    used = other.values()
    used += list(dsgroup-dsaxgroup[ax.name])
    saved = list(dsaxgroup[ax.name])
    while None in saved:
        saved.remove(None)
    while None in used:
        used.remove(None)
    value = available[0]
    if hasattr(ax, 'm_auto') and name in ax.m_auto:
        value = ax.m_auto[name]
        logging.debug('select_ax_value: m_auto override',ax.name, value, ax.m_auto)
    elif len(saved):
        value = list(saved)[0]
        logging.debug('select_ax_value: saved', ax.name, value)
    else:
        value = find_unused(used, available)
        logging.debug('select_ax_value: unused', ax.name, value)           
    return value

def read_rule_style(dsname):
    m = confdb.rule_style(dsname, latest=True)
    logging.debug('Apply saved style', dsname,m)
    if not m:
        return ['','',0,0,0]
    return m

def load_rules(doc, tree):
    """Load styling rules for involved axes and curves"""
    rule_by_dataset = {}
    rule_by_ax = {}
    for plotpath in tree['plot']:
        plot = doc.resolveFullWidgetPath(plotpath)
        y = plot.settings['yData']
        m = read_rule_style(y)
        if m:
            rule_by_dataset[y] = m
            rule_by_ax[plot.settings['yAxis']] = m
            
    return rule_by_dataset, rule_by_ax
    
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
            

    def arrange_axes(self, tree, graph, rule_by_ax):
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
            axmarkers[ax.name] = veusz.utils.MarkerCodes[idx]
            
        # Read saved dataset formats
        dataset_ax_colors = defaultdict(set)
        dataset_ax_styles = defaultdict(set)
        dataset_ax_markers = defaultdict(set)
        dataset_colors = set()
        dataset_styles = set()
        dataset_markers = set()
        
        for ds in self.doc.data.values():

            c = ds.attr.get(graph+'|PlotLine/color', None)
            if c is None:
                continue
            axpath = ds.attr.get(graph+':ax', None)
            if axpath is None:
                continue
            
            dataset_ax_colors[axpath].add(c)
            dataset_colors.add(c)
            s = ds.attr.get(graph+'|PlotLine/style', None)
            dataset_styles.add(s)
            dataset_ax_styles[axpath].add(s)
            s = ds.attr.get(graph+'|marker', None)
            dataset_markers.add(s)
            dataset_ax_markers[axpath].add(s)              
        
        
        # Total axes for repositioning
        if len(axes) > 1:
            tot = 1. / (len(axes) - 1)
        else:
            tot = 0
        
        for idx, axpath in enumerate(axes):
            props = {}
            ax = self.doc.resolveFullWidgetPath(axpath)

            axcolors[ax.name] = select_ax_value(axcolors, ax, 
                                             dataset_colors, 
                                             dataset_ax_colors, 
                                             kelly_colors, 
                                             'Line/color')
            axstyles[ax.name] = select_ax_value(axstyles, ax,
                                             dataset_styles,
                                             dataset_ax_styles,
                                             lineStyles,
                                             'Line/style')
            axmarkers[ax.name] = select_ax_value(axmarkers, ax,
                                              dataset_markers,
                                              dataset_ax_markers,
                                              veusz.utils.MarkerCodes,
                                              'marker')
                
            # Rule override
            rule = rule_by_ax.get(ax.name, ['','',0,0,0])
            C,L,M = rule[2:] 
            if C: axcolors[ax.name] = C
            if L: axstyles[ax.name] = L
            if M: axmarkers[ax.name] = M
            
            props = {}
            if self.fields['axis'] == 'Line Color' or C:
                value = axcolors[ax.name]
                props.update({'Line/color': value,
                         'Label/color': value,
                         'TickLabels/color': value,
                         'MajorTicks/color': value,
                         'MinorTicks/color': value})
                
            if self.fields['axis']=='Line Style' or L:
                props.update({'Line/style': axstyles[ax.name]})
                
            if self.fields['axis']=='Point Marker' or M:
                if not hasattr(ax, 'm_auto'):
                    ax.m_auto={}
                ax.m_auto['marker'] = axmarkers[ax.name]

            # Reposition
            if self.fields['space']:
                props['otherPosition'] = idx * tot
                
            # Set saved range
            if ':' in rule[0]:
                props['min'], props['max'] = map(lambda s: s if s=='Auto' else float(s), rule[0].split(':'))
            if rule[1]:
                props['datascale'] = float(rule[1])
                

            self.dict_toset(ax, props, preserve=True)
        
        return axes, axcolors, axstyles, axmarkers

    def arrange_curve(self, plotpath, tree, axes, axcolors, axstyles, axmarkers, 
                      smps):
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
        
        if plotted_dataset_names and (y not in plotted_dataset_names):
            return obj
        
        ###################
        # AXIS GROUPING
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
        
        ###################        
        # PATH GROUPING
        s= '/'.join(y.split('/')[:-1])
        other = smps.copy()
        other.pop(s)
        used = other.values()
    
        def select_path_value(used0, name, available):
            saved = set()
            map(saved.update, list(u['saved:'+name] for u in used0))
            if None in saved:
                saved.remove(None)
            used = set()
            map(used.update, list(u[name] for u in used0))
            
            v = find_unused(used, available)
            logging.debug('select_path_value found', name, v, used) 
            return v 
        
        if self.fields['path']=='Line Color':
            v = select_path_value(used, 'color', kelly_colors)
            props.update({'color': v, 
                     'PlotLine/color': v,
                     'MarkerFill/color': v,
                     'MarkerLine/color': v})
            smps[s]['color'].add(v)
        elif self.fields['path']=='Line Style':
            v = select_path_value(used, 'style', lineStyles)
            props['PlotLine/style'] = v
            smps[s]['style'].add(v)
        elif self.fields['path'] == 'Point Marker':
            v = select_path_value(used, 'marker', veusz.utils.MarkerCodes)
            props['marker'] = v
            smps[s]['marker'].add(v)
        
        
        # Apply rules    
        style_color, style_line, style_marker = read_rule_style(y)[2:]
        for k in props:
            if style_color and k.endswith('color'):
                props[k] = style_color
            if style_line and k.endswith('style'):
                props[k] = style_line
            if style_marker and k.endswith('marker'):
                props[k] = style_marker
                
        # Override with any property saved in dataset attr
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
        
        # Load rules:
        rule_by_dataset, rule_by_ax = load_rules(self.doc, tree)

        # Ax Positioning
        axes, axcolors, axstyles, axmarkers = self.arrange_axes(tree, graph, rule_by_ax)
        
        
        # Set plot colors based on axis colors
        
        plots = []
        smps = defaultdict(lambda: defaultdict(set))
        for plotpath in tree['plot']:
            plot = self.doc.resolveFullWidgetPath(plotpath)
            y = plot.settings['yData']
            s= '/'.join(y.split('/')[:-1])
            ds = self.doc.data[y]
            smps[s]['color'].add(plot.settings.PlotLine['color'])
            smps[s]['style'].add(plot.settings.PlotLine['style'])
            smps[s]['marker'].add(plot.settings['marker'])
            smps[s]['saved:color'].add(ds.attr.get(graph+'|PlotLine/color', None))
            smps[s]['saved:style'].add(ds.attr.get(graph+'|PlotLine/style', None))
            smps[s]['saved:marker'].add(ds.attr.get(graph+'|marker', None))
            
            plots.append(plot)
        
        for plotpath in tree['plot']:
            plot = self.arrange_curve(
                plotpath, tree, axes, axcolors, axstyles, axmarkers,
                smps)
            
        self.apply_ops()
        
        for plot in plots:
            save_plot_style_in_dataset_attr(plot, self.cmd)


plugins.toolspluginregistry.append(ArrangePlugin)
