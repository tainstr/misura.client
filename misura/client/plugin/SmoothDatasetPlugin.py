#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import numpy
from utils import smooth


class SmoothDatasetPlugin(plugins.DatasetPlugin):

    """Dataset plugin to smooth data values"""
    # tuple of strings to build position on menu
    menu = ('Filter', 'Smoothing')
    # internal name for reusing plugin later
    name = 'SmoothData'
    # string which appears in status bar
    description_short = 'Smooth data'

    # string goes in dialog box
    description_full = ('Smooth data.'
                        'Smooth data.')

    def __init__(self, ds_in='', method='hanning', window=5, ds_out='', end_index=0):
        """Define input fields for plugin."""

        self.fields = [
            plugins.FieldDataset(
                'ds_in', 'Dataset to be smoothed', default=ds_in),
            plugins.FieldCombo('method', 'Smoothing method', default=method, items=(
                'flat', 'hanning', 'hamming', 'bartlett', 'blackman', 'kaiser'), editable=False),
            plugins.FieldInt('window', 'Window length', default=window),
            plugins.FieldInt('start_index', 'Start index', minval=0, default=0),
            plugins.FieldInt('end_index', 'End index (0 = last)', minval=0, default=end_index),
            plugins.FieldDataset(
                'ds_out', 'Output dataset name', default=ds_out)
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
        # return list of datasets
        return [self.ds_out]

    def updateDatasets(self, fields, helper):
        """Do shifting of dataset.
        This function should *update* the dataset(s) returned by getDatasets
        """
        # get the input dataset - helper provides methods for getting other
        # datasets from Veusz
        ds_in = helper.getDataset(fields['ds_in'])
        # get the value to add
        window = fields['window']
        method = fields['method']
        start_index = fields['start_index']
        end_index = fields['end_index']

        if end_index == 0:
            end_index = len(ds_in.data)

        x = numpy.array(ds_in.data)
        x = x[start_index:end_index]

        if ds_in == helper.getDataset(fields['ds_out']):
            raise plugins.DatasetPluginException(
                "Input and output datasets should differ.")
        if x.ndim != 1:
            raise plugins.DatasetPluginException(
                "smooth only accepts 1 dimension arrays.")
        if x.size < window:
            raise plugins.DatasetPluginException(
                "Input vector needs to be bigger than window size.")
        if window < 3:
            raise plugins.DatasetPluginException("Window is too small.")
        if not method in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
            raise plugins.DatasetPluginException(
                "Mehtod is one of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")
        y = smooth(x, window, method)
        y = numpy.concatenate((ds_in.data[0:start_index], y, ds_in.data[end_index:]))

        # update output dataset with input dataset (plus value) and errorbars
        self.ds_out.update(
            data=y, serr=ds_in.serr, perr=ds_in.perr, nerr=ds_in.nerr)
        return [self.ds_out]

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(SmoothDatasetPlugin)
