#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Intercept all curves in a given x or y by placing datapoints."""
from misura.canon.logger import Log as logging
import veusz.widgets
import veusz.plugins as plugins
import veusz.document as document
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
                 text='Intercept\\\\%(xlabel)s=%(x).0f\\\\%(ylabel)s=%(y)E'):
        """Make list of fields."""
        self.fields = [
            plugins.FieldDatasetMulti(
                "target", descr="Datasets whose curves to intercept", default=target),
            plugins.FieldCombo(
                "axis", descr="Intercept on X or Y axis", items=['X', 'Y'], default=axis),
            plugins.FieldFloat('val', 'Value', default=val),
            plugins.FieldCombo("search", descr="Place nearest", items=[
                               'Nearest (Fixed X)', 'Nearest', 'Maximum', 'Minimum', 'Inflection', 'Stationary'], default=search),
            plugins.FieldFloat(
                'searchRange', descr='Nearest search range', default=searchRange),
            plugins.FieldDataset('critical_x',descr="Critical search X dataset", default=critical_x),
            plugins.FieldText('text', 'Label text', default=text),
        ]

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
        basename = fields.get('basename', False)
        targetds = fields['target']
#		targetds=target
        doc = cmd.document

        hor = axn == 'X'
        actions = []
        logging.debug('%s %s', 'targets', targetds)
        for obj in g.children:
            if not isinstance(obj, veusz.widgets.point.PointPlotter):
                continue
            if obj.settings.hide:
                logging.debug('%s %s', 'Skipping hidden object', obj.path)
                continue
            if obj.settings.yData not in targetds and len(targetds) > 0:
                logging.debug(
                    '%s %s %s', 'Skipping non-targeted object', obj.path, obj.settings.yData)
                continue
            # Search the nearest point
            x = obj.settings.get('xData').getFloatArray(doc)
            y = obj.settings.get('yData').getFloatArray(doc)
            dst = abs(x - val) if hor else abs(y - val)
            i = np.where(dst == dst.min())[0]
            if len(i) == 0:
                raise plugins.ToolsPluginException(
                    'Impossible to find required value: %E' % val)
            i = i[0]
            # Add the datapoint
            cmd.To(g.path)
            name = g.createUniqueName(
                'datapoint_' + obj.name) if not basename else basename + '_' + obj.name
            lblname = name + '_lbl'
            # Create the output label
            self.ops.append(
                document.OperationWidgetAdd(g, 'label', name=lblname))
            # Create the datapoint
            dpset = {'name': name, 'xy': obj.name,
                     'xAxis': obj.settings.xAxis, 'yAxis': obj.settings.yAxis,
                     'xPos': float(x[i]), 'yPos': float(y[i]),
                     'coordLabel': lblname, 'labelText': text,
                     'search': fields['search'], 'searchRange': fields['searchRange'],
                     'critical_x':fields['critical_x']}
            self.ops.append(
                document.OperationWidgetAdd(g, 'datapoint', **dpset))
            # Apply operation list
# 			doc.applyOperation(document.OperationMultiple(self.ops, descr='intercept'))
            # Call the update action in order to correctly position the
            # datapoints
            actions.append(g.path + '/' + name)

# 			cmd.To(g.path + '/' + name)
# 			cmd.Action('up')

        logging.debug('%s %s', 'Intercepting', self.ops)
        self.apply_ops('Intercept')
        # Force update call
        for p in actions:
            cmd.To(p)
            cmd.Action('up')


plugins.toolspluginregistry.append(InterceptPlugin)
