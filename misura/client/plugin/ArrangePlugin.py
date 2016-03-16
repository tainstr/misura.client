#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Arrange curves and axes"""
from misura.canon.logger import Log as logging
import veusz.plugins as plugins
import veusz.utils
from misura.client.iutils import get_plotted_tree
from misura.client.colors import colorize, colorLevels
import utils
from matplotlib.axis import YAxis

lineStyles = ['solid', 'dashed', 'dotted', 'dash-dot',
              'dash-dot-dot', 'dotted-fine', 'dashed-fine', 'dash-dot-fine',
              'dot1', 'dot2', 'dot3', 'dot4', 'dash1', 'dash2', 'dash3', 'dash4',
              'dash5', 'dashdot1', 'dashdot2', 'dashdot3']

defvars = {'Line Style': ('PlotLine/style', 'm_style', 'solid'),
           'Line Color': ('PlotLine/color', 'm_color', '#000000'),
           'Point Marker': ('marker', 'm_marker', 'none')
           }


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
            axcolors[ax.name] = ax.settings.Line.color

        if len(axes) > 1:
            tot = 1. / (len(axes) - 1)
        else:
            tot = 0

        levels = len(axes)
        LR, LG, LB = colorLevels(levels)
        dcolor = 0  # color skipping delta
        used = axcolors.viewvalues()  # already used colors
        for idx, axpath in enumerate(axes):
            ax = self.doc.resolveFullWidgetPath(axpath)
            color = '#000000'
            # Generate html color for this idx
            if self.fields['dataset'] == 'Line Color':
                if hasattr(ax, 'm_auto'):
                    color = ax.m_auto.get('Line/color', False)
                    logging.debug('%s %s', 'm_auto', color)
                else:
                    color = colorize(idx + dcolor, LR, LG, LB)
                    logging.debug('%s %s', 'found color', color)
                    while color in used:
                        logging.debug('%s %s', 'color is used', color)
                        dcolor += 1
                        levels += 1
                        LR, LG, LB = colorLevels(levels)
                        color = colorize(idx + dcolor, LR, LG, LB)

            axcolors[ax.name] = color
            props = {'Line/color': color,
                     'Label/color': color,
                     'TickLabels/color': color,
                     'MajorTicks/color': color,
                     'MinorTicks/color': color}
            # Reposition
            if self.fields['space']:
                props['otherPosition'] = idx * tot
            self.dict_toset(ax, props)
        return axes, axcolors
    
    def arrange_curve(self, plotpath, tree, axes, axcolors, var, m_var, LR, LG, LB, unused_formatting_opt):
        # Set colors according to axes
        obj = self.doc.resolveFullWidgetPath(plotpath)

        plotted_curve = self.fields.get('plotted_curve', False)
        current_curve = obj.settings['yData']

        if not plotted_curve or plotted_curve in current_curve:
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
            props['marker'] = 'none'
        
        # Get dataset for marker setting
        y = obj.settings['yData']
        if not self.doc.data.has_key(y):
            self.dict_toset(obj, props)
            return False
        ds = self.doc.data[y]
        smp = getattr(ds, 'm_smp', False)
        if not smp:
            self.dict_toset(obj, props)
            return False

        # Set the unused style component to default
        uvar, um_var, udefvar = defvars[unused_formatting_opt]
        props[uvar] = udefvar
        setattr(smp, um_var, udefvar)

        # Secondary style value
        ax_datasets = tree['axis'][yax.path]
        if y in ax_datasets:
            idx = ax_datasets.index(y)
        else:
            idx = 0
        if m_var == 'm_marker':
            outvar = veusz.utils.MarkerCodes[idx]
        elif m_var == 'm_style':
            outvar = lineStyles[idx]
        elif m_var == 'm_color':
            outvar = colorize(idx, LR, LG, LB)

        props[var] = outvar
        setattr(smp, m_var, outvar)

        if smp.ref:
            self.dict_toset(obj, props)
            return False

        refsmp = ds.linked.samples[0]
        refvar = getattr(refsmp, m_var)
        smpvar = getattr(smp, m_var)
        # Recover the linestyle from the reference sample
        if smp['idx'] == 0 and refvar not in ['none', False]:
            setattr(smp, m_var, refvar)
            props[var] = refvar
            
        # Set back the reference marker if it was not set and this is the
        # first sample
        if smp['idx'] == 0:
            logging.debug(
                '%s %s %s %s', 'Setting back reference marker', smp, refsmp, outvar)
            setattr(refsmp, m_var, outvar)
        self.dict_toset(obj, props)
        return True
        
    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.doc = cmd.document
        self.fields = fields
        if fields['sample'] == fields['dataset']:
            raise plugins.ToolsPluginException(
                'You must choose different markers for Datasets and Samples.')
        
        unused_formatting_opt = set(defvars.keys()) - set([fields['sample'], fields['dataset']])
        unused_formatting_opt = list(unused_formatting_opt)[0]

        # Search for the graph widget
        gobj = self.doc.resolveFullWidgetPath(fields['currentwidget'])
        gobj = utils.searchFirstOccurrence(gobj, 'graph')
        if gobj is None or gobj.typename != 'graph':
            raise plugins.ToolsPluginException(
                'You should run this tool on a graph')

        graph = gobj.path
        tree = get_plotted_tree(gobj)
        logging.debug('%s %s %s %s', 'Plotted axis', graph, tree['axis'], tree)
        smps = tree['sample']
        
        # Ax Positioning
        axes, axcolors = self.arrange_axes(tree, graph)
        
        # Set plot colors based on axis colors
        var, m_var, defvar = defvars[fields['sample']]
        LR, LG, LB = colorLevels(len(smps))
        for plotpath in tree['plot']:
            self.arrange_curve(plotpath, tree, axes, axcolors, var, m_var, LR, LG, LB, unused_formatting_opt)
            
        self.apply_ops()

plugins.toolspluginregistry.append(ArrangePlugin)
