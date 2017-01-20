#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
from PyQt4 import QtGui, QtCore
import veusz.document as document
import utils

from misura.client.iutils import get_plotted_tree
from .. import units


class PercentilePlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Convert to percentile value"""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Percentile')
    # internal name for reusing plugin later
    name = 'Percentile'
    # string which appears in status bar
    description_short = 'Convert to/from percentile values'

    # string goes in dialog box
    description_full = (
        'Convert to percentile values, given an initial dimension')

    def __init__(self, ds='', propagate=False, action='Invert', auto=True):
        """Define input fields for plugin."""
        self.fields = [
            plugins.FieldDataset('ds', 'Dataset to convert', default=ds),
            plugins.FieldBool(
                "propagate", descr="Apply to all datasets sharing the same Y axis:", default=propagate),
            plugins.FieldCombo("action", descr="Conversion mode:", items=[
                               'Invert'], default=action),
            plugins.FieldBool(
                "auto", descr="Auto initial dimension", default=auto)
        ]

    def apply(self, interface, fields):
        """Do the work of the plugin.
        interface: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.doc = interface.document
        # raise DatasetPluginException if there are errors
        ds = interface.document.data.get(fields['ds'], False)
        if not ds:
            raise plugins.DatasetPluginException(
                'Dataset not found' + fields['ds'])

        action = units.percentile_action(ds, fields['action'])
        ds1 = units.percentile_conversion(ds, action, fields['auto'])
        ds = ds1
        self.ops.append(document.OperationDatasetSet(fields['ds'], ds))
        #self.ops.append(document.OperationDatasetSetVal(fields['ds'], 'data',slice(None,None),ds1.data[:]))

        self.apply_ops()
        logging.debug('Converted %s %s using initial dimension %.2f.' % (
            fields['ds'], fields['action'], ds.m_initialDimension))
# 		QtGui.QMessageBox.information(None,'Percentile output',
# 				'Converted %s %s using initial dimension %.2f.' % (fields['ds'], msg, ds.m_initialDimension))

        # updating all dependent datapoints
        convert_func = units.percentile_func(ds, action, fields['auto'])
        utils.convert_datapoint_units(convert_func, fields['ds'], self.doc)

        if not fields['propagate']:
            return
        # Find all datasets plotted with the same Y axis
        cvt = []
        tree = get_plotted_tree(self.doc.basewidget)
        upax = []
        for axp, dslist in tree['axis'].iteritems():
            if not fields['ds'] in dslist:
                continue
            logging.debug('Propagating to', cvt)
            cvt += dslist
            upax.append(axp)
        cvt = list(set(cvt))
        if fields['ds'] in cvt:
            cvt.remove(fields['ds'])
        act = 'To Percent' if ds.m_percent else 'To Absolute'
        # Create a non-propagating percentile operation for each dataset found
        for nds in cvt:
            ncur = getattr(self.doc.data[nds], 'm_percent', None)
            if ncur == ds.m_percent:
                continue
            logging.debug('Really propagating percentile to', nds)
            fields = {
                'ds': nds, 'propagate': False, 'action': act, 'auto': True}
            self.ops.append(
                document.OperationToolsPlugin(PercentilePlugin(), fields))
        # Update axis labels
        old = units.symbols.get(ds.old_unit, False)
        new = units.symbols.get(ds.unit, False)
        if old and new:
            for ax in upax:
                ax = self.doc.resolveFullWidgetPath(ax)
                lbl = ax.settings.label.replace(old, new)
                self.toset(ax, 'label', lbl)
        # Apply everything
        self.apply_ops('Percentile: Propagate')


plugins.toolspluginregistry.append(PercentilePlugin)
