#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Changes measurement unit to a dataset."""
from misura.canon.logger import Log as logging
import veusz.plugins as plugins
import veusz.document as document
import utils
from .. import units
from misura.client.iutils import get_plotted_tree


class UnitsConverterTool(utils.OperationWrapper, plugins.ToolsPlugin):

    """Convert between measurement units"""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Change Unit')
    # internal name for reusing plugin later
    name = 'Units Converter'
    # string which appears in status bar
    description_short = 'Convert between measurement units'

    # string goes in dialog box
    description_full = ('Convert dataset to different measurement unit')

    def __init__(self, ds='', propagate=False, convert='None'):
        """Define input fields for plugin."""

        kgroup, f, p = units.get_unit_info(convert, units.from_base)
        items = units.from_base.get(kgroup, {convert: lambda v: v}).keys()
        self.fields = [
            plugins.FieldDataset('ds', 'Dataset to convert', default=ds),
            plugins.FieldCombo(
                "convert", descr="Convert to:", items=items, default=convert),
            plugins.FieldBool(
                "propagate", descr="Apply to all datasets sharing the same Y axis:", default=propagate),
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
        
        ds1 = units.convert(ds, fields['convert'])
        self.ops.append(document.OperationDatasetSet(fields['ds'], ds1))
        self.apply_ops()

        ####
        # PROPAGATION
        if not fields['propagate']:
            return
        # Find all datasets plotted with the same Y axis
        cvt = []
        tree = get_plotted_tree(self.doc.basewidget)
        upax = []
        for axp, dslist in tree['axis'].iteritems():
            if not fields['ds'] in dslist:
                continue
            logging.debug('%s %s', 'Propagating to', cvt)
            cvt += dslist
            upax.append(axp)
        # If time dataset, propagate to all time datasets
        if ds.m_var == 't':
            for k, nds in self.doc.data.iteritems():
                if k == fields['ds']:
                    continue
                if nds.m_var != 't':
                    continue
                cvt.append(k)
        cvt = list(set(cvt))
        # Create a non-propagating unit conversion operation for each dataset
        # found
        for nds in cvt:
            if nds == fields['ds']:
                continue
            ncur = getattr(self.doc.data[nds], 'unit', False)
            if not ncur:
                continue
            logging.debug(
                '%s %s', 'Really propagating unit conversion to', nds)
            fields = {
                'ds': nds, 'propagate': False, 'convert': fields['convert']}
            self.ops.append(
                document.OperationToolsPlugin(UnitsConverterTool(), fields))
        # Update axis labels
        old = units.symbols.get(ds.unit, False)
        new = units.symbols.get(fields['convert'], False)
        if old and new:
            for ax in upax:
                ax = self.doc.resolveFullWidgetPath(ax)
                lbl = ax.settings.label.replace(old, new)
                self.toset(ax, 'label', lbl)

        # Apply everything
        self.apply_ops('UnitsConverterTool: Propagate')


plugins.toolspluginregistry.append(UnitsConverterTool)
