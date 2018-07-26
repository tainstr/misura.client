#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import numpy as np
from scipy import fftpack
from utils import smooth


class FFTPlugin(plugins.DatasetPlugin):

    """Dataset plugin to compute Fast Fourier Transform"""
    # tuple of strings to build position on menu
    menu = ('Compute', 'FFT')
    # internal name for reusing plugin later
    name = 'FFT'
    # string which appears in status bar
    description_short = 'FFT'

    # string goes in dialog box
    description_full = 'Fast Fourier Transform'

    def __init__(self, ds_in='', ds_out=''):
        """Define input fields for plugin."""

        self.fields = [
            plugins.FieldDataset(
                'ds_in', 'Input dataset', default=ds_in),
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
        self.ds_out_freq = plugins.Dataset1D(fields['ds_out']+'_x')
        # return list of datasets
        return [self.ds_out, self.ds_out_freq]

    def updateDatasets(self, fields, helper):
        """Do shifting of dataset.
        This function should *update* the dataset(s) returned by getDatasets
        """
        # get the input dataset - helper provides methods for getting other
        # datasets from Veusz
        ds_in = helper.getDataset(fields['ds_in'])
        
        if ds_in == helper.getDataset(fields['ds_out']):
            raise plugins.DatasetPluginException(
                "Input and output datasets should differ.")
            
        y = np.array(ds_in.data)
        
        if y.ndim != 1:
            raise plugins.DatasetPluginException(
                "FFT only accepts 1 dimension arrays.")
        
        N = len(y)
        
        yf = fftpack.fft(y)
        xf = np.arange(int(N/2))

        # update output dataset with input dataset (plus value) and errorbars
        self.ds_out.update(data=yf)
        self.ds_out_freq.update(data=xf)
        return [self.ds_out, self.ds_out_freq]

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(FFTPlugin)
