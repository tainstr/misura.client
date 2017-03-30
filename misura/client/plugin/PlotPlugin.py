#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Custom Misura plotting facilities."""
import veusz.plugins as plugins
import veusz.document as document
from ArrangePlugin import ArrangePlugin
from time import time
from misura.client.iutils import get_plotted_tree
import os
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import utils
import PercentPlugin
from .. import units

default_curves = ['T', 'P', 'S', 'h', 'Vol', 'd', 'err']
an_default_curves = ['T', 'Vol', 'd', 'Dil',  'Sint', 'Flex']

power_axes = {'kiln/P': 'Power', 'kiln/kP': 'Power', 'kiln/kI': 'Power',
              'kiln/kD': 'Power', 'kiln/pC': 'Power', 'kiln/pD': 'Power',
              'kiln/T': 'Temperature', 'kiln/S': 'Temperature'}

# TODO: This should be a configurable rule_ construct of ConfDb
bounded_axes = {'odlt': {'camA': 'Dil', 'camB': 'Dil', 'const': 'pos'},
                'odht': {'camA': 'Dil', 'camB': 'Dil', 'const': 'pos'},
                'flex': {'camA': 'Flex', 'const': 'pos'},
                'hsm': {},
                'kiln': {},
                }

for key in bounded_axes.keys():
    d = bounded_axes[key]
    d.update(power_axes)
    bounded_axes[key] = d


def dataset_curve_name(ds, dsn):
    """Generation of unambiguous and traceable curve and axis names"""
    sampleName = ''
    if getattr(ds, 'm_smp', False):
        if len(ds.linked.instr.list()) <= 2:
            sampleName = ''
        elif ds.m_smp.has_key('name'):
            sampleName = ds.m_smp['name']
        else:
            sampleName = ds.linked.instr.measure['name']
    dsname = getattr(ds, 'm_name', dsn).replace(
        'summary/', '')
    instrument_name = dsname.split('/')[0]
    if ':' in instrument_name:
        instrument_name = instrument_name.split(':')[1]
    dsname = dsname.replace("/", ":")
    dsvar = getattr(ds, 'm_var', '')
    fileName = '' if ds.linked is None else os.path.basename(
        ds.linked.filename)
    if sampleName:
        curve_name = unicode(dsname + ' - ' + sampleName + ' - ' + fileName)
    else:
        curve_name = unicode(dsname + ' - ' + fileName)
    bounded_name = bounded_axes.get(instrument_name, {}).get(dsvar, dsvar)
    ax_label = bounded_name
    unit = ds.unit or getattr(getattr(ds, 'parent', False), 'unit', False)
    if unit:
        u = units.symbols.get(unit, unit)
        ax_label += ' ({{{}}})'.format(u)
    ax_name = 'ax:' + bounded_name.replace("/", ":")
    return curve_name, ax_name, ax_label


class PlotDatasetPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Plot Misura datasets."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Plot a list of misura x,y couples')
    # unique name for plugin
    name = 'Plot datasets'
    # name to appear on status tool bar
    description_short = 'Plot lists of Misura datasets'
    # text to appear in dialog box
    description_full = 'Plot lists of Misura datasets in a consistent way'

    def __init__(self, x=[], y=[]):
        """Make list of fields."""

        self.fields = [
            plugins.FieldDatasetMulti("x", 'X Coord datasets', default=[]),
            plugins.FieldDatasetMulti("y", 'Y Coord datasets', default=[]),
        ]

    def initCurve(self, name='Curve', xData='xD', yData='yD',
                  yAxis='y', axisLabel='Curve', graph='/page/graph'):
        """Configure a new curve (appearance, axes positions, data labels"""
        logging.debug('initCurve', name, xData, yData)

        doc = self.doc

        gobj = doc.resolveFullWidgetPath(graph)
        preop = []
        preop.append(document.OperationWidgetAdd(gobj, 'xy', name=name))
        create = True
        for obj in gobj.children:
            if obj.name == yAxis:
                create = False
                break
        if create:
            preop.append(document.OperationWidgetAdd(
                gobj, 'axis-function', name=yAxis, direction='vertical'))

        # Create graph and axis (if needed)
        logging.debug('applying operations', preop)
        doc.applyOperation(
            document.OperationMultiple(preop, descr='PlotDataset:Create'))

        obj = gobj.getChild(name)
        n = len(doc.data[yData].data)
        thin = int(max(1, n / 100))
        if n > 10:
            self.toset(obj, 'marker', u'none')
        else:
            self.toset(obj, 'marker', u'circle')
        self.toset(obj, 'markerSize', u'2pt')
        self.toset(obj, 'thinfactor', thin)
        self.toset(obj, 'yData', yData)
        self.toset(obj, 'xData', xData)
        self.toset(obj, 'key', name.replace('_', '\\_'))
        self.toset(obj, 'yAxis', yAxis)

        yax = gobj.getChild(yAxis)
        self.toset(
            yax, 'label', axisLabel.replace('_', '\\_').replace('/', '.'))
        self.apply_ops('PlotDataset:Associate')
        return True

    def auto_percent(self, ds, dsn, gname, ax_name):
        """Find if the dataset ds should be converted to percentage based on other datasets sharing the same Y ax."""
        g = self.doc.resolveFullWidgetPath(gname)
        tree = get_plotted_tree(g)
        dslist = tree['axis'].get(g.path + '/' + ax_name, [])

        is_derived = getattr(ds, 'ds', ds) 
        is_derived = isinstance(is_derived, document.datasets.Dataset1DPlugin)
        if is_derived:
            ds.m_initialDimension = getattr(ds.parent.ds,
                                            'm_initialDimension',
                                            None)

        pc = getattr(ds, 'm_percent', None)
        if pc is None:
            logging.debug('No m_percent attribute defined', dsn)
            return False

        cvt = None
        for nds in dslist:
            if nds == dsn:
                continue  # itself
            cvt = getattr(self.doc.data[nds], 'm_percent', None)
            if cvt is not None:
                break
        if cvt is None or cvt == pc:
            return False
        # A conversion should happen
        logging.debug('CONVERTING', cvt, pc)
        self.ops.append(document.OperationToolsPlugin(
            PercentPlugin.PercentPlugin(),
            {
                'ds': dsn,
                'propagate': False,
                'action': 'Invert',
                'auto': False
            })
        )
        return True

    def arrange(self, graphics_names, plotted_dataset_names=False):
        arrange_fields = {'currentwidget': '/time/time',
                          'dataset': 'Line Color',
                          'sample': 'Line Style',
                          'space': True,
                          'plotted_dataset_names': plotted_dataset_names}

        for gname in graphics_names:
            arrange_fields['currentwidget'] = gname
            self.ops.append(
                document.OperationToolsPlugin(ArrangePlugin(),
                                              arrange_fields.copy()))

        self.apply_ops('PlotDataset: Arrange')

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        doc = cmd.document
        self.doc = doc
        self.cmd = cmd

        cur = fields['currentwidget']
        g = self.doc.resolveFullWidgetPath(cur)
        g = utils.searchFirstOccurrence(g, 'graph')
        if g is None or g.typename != 'graph':
            raise plugins.ToolsPluginException(
                'You should run this tool on a graph')

        logging.debug('Plotting:', fields['x'], fields['y'])
        cnames = {}
        doc = cmd.document
        t = time()
        gnames = []
        n = 0
        valid_x, valid_y = [], []
        for i, x in enumerate(fields['x']):
            y = fields['y'][i]
            if not (doc.data.has_key(x)and doc.data.has_key(y)):
                continue
            valid_x.append(x)
            valid_y.append(y)
            n += self.validate_datasets((doc.data[x], doc.data[y]))
        if n > 0:
            # TODO: reload document!
            pass

        for i, x in enumerate(valid_x):
            y = valid_y[i]
            logging.debug('plotting value:', y, 'data:', doc.data[y])
            ds = doc.data[y]
            # If the ds is recursively derived, substitute it by its entry
            if not hasattr(ds, 'm_smp'):
                logging.debug('Retrieving ent', y)
                ds = doc.ent.get(y, False)

            # Get the curve and axis name
            cname, ax_name, ax_lbl = dataset_curve_name(ds, y)

            gname = g.path

            self.auto_percent(ds, y, gname, ax_name)

            self.initCurve(name=cname, xData=x, yData=y,
                           yAxis=ax_name, axisLabel=ax_lbl, graph=gname)
            if gname not in gnames:
                gnames.append(gname)
            cnames[y] = cname

        self.apply_ops('PlotDataset: Customize')
        if len(fields) > 0 and len(fields['y']) > 0:
            self.arrange(gnames, fields['y'])

        return cnames


# INTENTIONALLY NOT PUBLISHED
# plugins.toolspluginregistry.append(PlotDatasetPlugin)
# plugins.toolspluginregistry.append(DefaultPlotPlugin)
