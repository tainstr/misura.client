#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Intercept all curves in a given x or y by placing datapoints."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.widgets
import veusz.plugins as plugins
import veusz.document as document
from veusz.dialogs.plugin import PluginDialog
import numpy as np
import utils


class InterceptPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Intercept all curves at a given x or y by placing datapoints"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Intercept')
    # unique name for plugin
    name = 'Intercept'
    # name to appear on status tool bar
    description_short = 'Intercept all sample\'s curves in a plot'
    # text to appear in dialog box
    description_full = 'Intercept all curves pertaining to a file, sample or dataset by placing descriptive datapoints'

    def __init__(self, target=[], axis='X', val=0., search='Nearest (Fixed X)', searchRange=25, critical_x='',
                 text='Intercept\\\\%(ylabel)s=%(y).1E\\\\T=%(T).1f\\\\t=%(t)i', currentwidget=False):
        """Make list of fields."""
        self.fields = [
            plugins.FieldDatasetMulti(
                "target", descr="Datasets whose curves to intercept", default=target),
            plugins.FieldCombo(
                "axis", descr="Intercept on X or Y axis", items=['X', 'Y'], default=axis),
            plugins.FieldFloat('val', 'Value', default=val),
            plugins.FieldCombo("search", descr="Place nearest", items=[
                               'Nearest (Fixed X)', 'Nearest', 'Maximum', 'Minimum', 'Inflection', 'Stationary', 'None'], default=search),
            plugins.FieldFloat(
                'searchRange', descr='Nearest search range', default=searchRange),
            plugins.FieldDataset('critical_x',descr="Critical search X dataset", default=critical_x),
            plugins.FieldText('text', 'Label text', default=text),
        ]

    @staticmethod
    def clicked_curve(mouse_position, main_window):
        plot = main_window.plot

        pickinfo = veusz.widgets.PickInfo()
        pos = plot.mapToScene(mouse_position)

        for w, bounds in plot.painthelper.widgetBoundsIterator():
            try:
                # ask the widget for its (visually) closest point to the cursor
                info = w.pickPoint(pos.x(), pos.y(), bounds)

                if info.distance < pickinfo.distance:
                    # and remember the overall closest
                    pickinfo = info
            except AttributeError:
                # ignore widgets that don't support axes or picking
                continue

        if not pickinfo:
            return
        
        curve_to_intercept = pickinfo.widget.settings['yData']
        p = InterceptPlugin(target=[curve_to_intercept],
                            axis='X',
                            critical_x='0:t',
                            currentwidget=main_window.plot.pickerwidgets[-1],
                            val=pickinfo.coords[0])
        d = PluginDialog(main_window, main_window._document, p, InterceptPlugin)
        main_window.showDialog(d)


    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.doc = cmd.document
        cur = fields['currentwidget']
        g = self.doc.resolveFullWidgetPath(cur)
        g = utils.searchFirstOccurrence(g, 'graph')
        if g is None or g.typename != 'graph':
            raise plugins.ToolsPluginException(
                'You should run this tool on a graph')
        axn = fields['axis']
        val = fields['val']
        text = fields['text']
        targetds = fields['target']
        doc = cmd.document

        hor = axn == 'X'
        datapoint_paths = []
        logging.debug( 'targets', targetds)
        for datapoint_parent in g.children:
            if not isinstance(datapoint_parent, veusz.widgets.point.PointPlotter):
                continue
            if datapoint_parent.settings.hide:
                logging.debug('Skipping hidden object', datapoint_parent.path)
                continue
            if datapoint_parent.settings.yData not in targetds and len(targetds) > 0:
                logging.debug('Skipping non-targeted object', datapoint_parent.path, 
                              datapoint_parent.settings.yData)
                continue
            # Search the nearest point
            x = datapoint_parent.settings.get('xData').getFloatArray(doc)
            y = datapoint_parent.settings.get('yData').getFloatArray(doc)
            dst = abs(x - val) if hor else abs(y - val)
            i = np.where(dst == dst.min())[0]
            if len(i) == 0:
                raise plugins.ToolsPluginException(
                    'Impossible to find required value: %E' % val)
            i = i[0]
            # Add the datapoint
            cmd.To(g.path)
            name = datapoint_parent.createUniqueName('datapoint')
            lblname = name + '_lbl'

            # Create the datapoint
            datapoint_settings = {'name': name,
                                  'xAxis': datapoint_parent.settings.xAxis,
                                  'yAxis': datapoint_parent.settings.yAxis,
                                  'xPos': float(x[i]),
                                  'yPos': float(y[i]),
                                  'coordLabel': lblname,
                                  'labelText': text,
                                  'search': fields['search'],
                                  'searchRange': fields['searchRange']}

            if fields.has_key('critical_x'):
                datapoint_settings['critical_x'] = fields['critical_x']

            self.ops.append(document.OperationWidgetAdd(datapoint_parent,
                                                        'datapoint',
                                                        **datapoint_settings))

            datapoint_paths.append(datapoint_parent.path + '/' + name)

        logging.debug('Intercepting', self.ops)
        self.apply_ops('Intercept')

        for path in datapoint_paths:
            cmd.To(path)
            cmd.Action('up')


plugins.toolspluginregistry.append(InterceptPlugin)
