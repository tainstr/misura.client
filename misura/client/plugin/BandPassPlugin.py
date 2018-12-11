#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Butterworth bandpass plugin"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.csutil import butter_bandpass_filter

import veusz.plugins as plugins
import numpy as np

class BandPassPlugin(plugins.DatasetPlugin):

    """Bandpass filtering with Butterworth filters"""
    # tuple of strings to build position on menu
    menu = ('Compute', 'BandPass')
    # internal name for reusing plugin later
    name = 'BandPass'
    # string which appears in status bar
    description_short = 'BandPass'

    # string goes in dialog box
    description_full = 'Bandpass with Butterworth filters'

    def __init__(self, ds_in='', ds_t='', max_freq=1000, min_freq=0, start_index=0, end_index=0, order=5, invert=False, ds_out=''):
        """Define input fields for plugin."""

        self.fields = [
            plugins.FieldDataset(
                'ds_in', 'Input dataset', default=ds_in),
            plugins.FieldDataset(
                'ds_t', 'Time dataset', default=ds_t),
            
            plugins.FieldInt('max_freq', 'Max frequency', minval=0, default=max_freq),
            plugins.FieldInt('min_freq', 'Min frequency', minval=0, default=min_freq),
            plugins.FieldInt('start_index', 'Start index', minval=0, default=start_index),
            plugins.FieldInt('end_index', 'End index (0 = last)', minval=0, default=end_index),
            plugins.FieldBool('invert', 'Suppress band', default=invert),
            plugins.FieldInt('order', 'Order', minval=0, default=order),
            
            plugins.FieldDataset(
                'ds_out', 'Output dataset', default=ds_out)
        ]

    def getDatasets(self, fields):
        """Returns single output dataset (self.ds_out).
        This method should return a list of Dataset objects, which can include
        Dataset1D, Dataset2D and DatasetText
        """
        # raise DatasetPluginException if there are errors
        if fields['ds_out'] == '':
            raise plugins.DatasetPluginException('Invalid output dataset name')
        # make a new dataset with name in fields['ds_out']
        logging.debug('DSOUT', fields)
        self.ds_out = plugins.Dataset1D(fields['ds_out'])
        #self.ds_out_t = plugins.Dataset1D(fields['ds_out']+'_t')
        # return list of datasets
        return [self.ds_out]#, self.ds_out_t]

    def updateDatasets(self, fields, helper):
        """Do shifting of dataset.
        This function should *update* the dataset(s) returned by getDatasets
        """
        # get the input dataset - helper provides methods for getting other
        # datasets from Veusz
        ds_in = helper.getDataset(fields['ds_in'])
        ds_t = helper.getDataset(fields['ds_t'])
        if helper.getDataset(fields['ds_out']) in (ds_in, ds_t, ''):
            raise plugins.DatasetPluginException(
                "Input and output datasets should differ.")
        start = fields.get('start_index', 0)
        end = fields.get('end_index', 0) or None
            
        y = np.array(ds_in.data)[start:end]
        t = np.array(ds_t.data)[start:end]
        if y.ndim != 1:
            raise plugins.DatasetPluginException(
                "BandPass only accepts 1 dimension arrays.")
        
        N = len(y)
        dt = np.diff(t).mean()
        max_freq = fields.get('max_freq', 0) or int(N/2)
        min_freq = fields.get('min_freq', 0)
        order = fields.get('order', 5)
        invert = fields.get('invert', False)
        yf = butter_bandpass_filter(y, min_freq, max_freq, 1./dt, order, invert)

        # update output dataset with input dataset (plus value) and errorbars
        self.ds_out.update(data=yf)
        #self.ds_out_t.update(data=t)
        return [self.ds_out]#, self.ds_out_t]

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(BandPassPlugin)
