#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Changes measurement unit to a dataset."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import veusz.document as document
import utils
from .. import units
from misura.client.iutils import get_plotted_tree

def update_unit_axis_labels(pluging_obj, ds, old, axis_paths):
    # Update axis labels
    new = units.symbols.get(ds.unit, False)
    if old and new:
        for ax_path in axis_paths:
            ax = pluging_obj.doc.resolveFullWidgetPath(ax_path)
            old_lbl = ax.settings.label
            if '({%})' in old_lbl or old_lbl.endswith('{%}'):
                lbl = old_lbl.replace('%', new)
            else:
                lbl = old_lbl.replace(old, new)
            if lbl!=old_lbl:
                pluging_obj.toset(ax, 'label', lbl)
                logging.debug('Replaxed axis label', ax_path, old_lbl, lbl)
            else:
                logging.debug('Did not replace axis label',ax_path, old_lbl, lbl, old, new)

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
        self.apply_fields = fields
        
        ds = interface.document.data.get(fields['ds'], False)
        if not ds:
            raise plugins.DatasetPluginException(
                'Dataset not found' + fields['ds'])
        old_unit = units.symbols.get(ds.unit, False)
        ds1 = units.convert(ds, fields['convert'])
        self.ops.append(document.OperationDatasetSet(fields['ds'], ds1))
        self.apply_ops()
        
        # Update DataPoints
        convert_func = units.convert_func(ds, fields['convert'])
        utils.convert_datapoint_units(convert_func, fields['ds'], self.doc)
        
        # Update file-wise time unit if ds is the time dataset
        if ds.linked and fields['ds']==ds.linked.prefix+'t':
            ds.linked.params.time_unit = ds1.unit
            
        ####
        # PROPAGATION
 
        # Find all datasets plotted with the same Y axis
        cvt = []
        tree = get_plotted_tree(self.doc.basewidget)
        upax = []
        for ax_path, dslist in tree['axis'].items():
            if not fields['ds'] in dslist:
                continue
            logging.debug('Propagating to', cvt)
            cvt += dslist
            upax.append(ax_path)
            
        # Add xaxis
        for ax_path, dslist in tree['xaxis'].items():
            if not fields['ds'] in dslist:
                print('SKIP XAXIS', ax_path, dslist)
                continue
            upax.append(ax_path)
               
        self.propagate(ds, cvt)
        
        update_unit_axis_labels(self, ds, old_unit, upax)

        # Apply everything
        self.apply_ops('UnitsConverterTool: dependencies')
        
    def propagate(self, ds, cvt):
        if not self.apply_fields['propagate']:
            return False
        
        # If time or temperature dataset, propagate to all time datasets
        if ds.m_var in ('t', 'T'):
            for k, nds in self.doc.data.iteritems():
                if k == self.apply_fields['ds']:
                    continue
                if getattr(nds, 'm_var', False) != ds.m_var:
                    continue
                cvt.append(k)
            
        cvt = list(set(cvt))
        # Create a non-propagating unit conversion operation for each dataset
        # found
        for nds in cvt:
            if nds == self.apply_fields['ds']:
                continue
            ncur = getattr(self.doc.data[nds], 'unit', False)
            if not ncur:
                continue
            logging.debug('Really propagating unit conversion to', nds)
            fields = {
                'ds': nds, 'propagate': False, 'convert': self.apply_fields['convert']}
            self.ops.append(
                document.OperationToolsPlugin(UnitsConverterTool(), fields))

plugins.toolspluginregistry.append(UnitsConverterTool)
