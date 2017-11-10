#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import veusz.plugins as plugins
import veusz.document as document
import numpy as np
import SmoothDatasetPlugin
from utils import MisuraPluginDataset1D

from misura.canon.logger import get_module_logging
logging = get_module_logging(__file__)

class CoefficientPlugin(plugins.DatasetPlugin):

    """Calculate a coefficient"""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Coefficient')
    # internal name for reusing plugin later
    name = 'Coefficient'
    # string which appears in status bar
    description_short = 'Calculate coefficient'

    # string goes in dialog box
    description_full = (
        'Calculate a coefficient between a fixed start value and any subsequent value in a curve')

    def __init__(self, ds_x='', ds_y='', start=50., percent=0., factor=1., 
                 reconfigure='Stop', smooth=5, smode='X and Y', linearize=150, ds_out='coeff'):
        """Define input fields for plugin."""
        self.fields = [
            plugins.FieldDataset('ds_x', 'X Dataset', default=ds_x),
            plugins.FieldDataset('ds_y', 'Y Dataset', default=ds_y),
            plugins.FieldFloat('start', 'Starting X value', default=start),
            plugins.FieldFloat(
                'percent', descr='Initial dimension', default=percent),
            plugins.FieldFloat(
                'factor', descr='Divide by', default=factor),
            plugins.FieldCombo('reconfigure', descr='When cooling is found', items=[
                               'Restart', 'Stop'], default=reconfigure),
            plugins.FieldInt('smooth', 'Smoothing Window', default=smooth),
            plugins.FieldCombo('smode', descr='Apply Smoothing to', items=[
                               'X and Y', 'Y alone', 'Output'], default=smode),
            plugins.FieldInt('linearize', 'Linearization window', default=linearize),
            plugins.FieldDataset(
                'ds_out', 'New output dataset name', default=ds_out),
        ]

    def getDatasets(self, fields):
        """Returns single output dataset (self.ds_out).
        This method should return a list of Dataset objects, which can include
        Dataset1D, Dataset2D and DatasetText
        """
        # raise DatasetPluginException if there are errors
        if fields['ds_x'] == fields['ds_y']:
            raise plugins.DatasetPluginException(
                'X and Y datasets cannot be the same')
        if fields['ds_out'] in (fields['ds_x'], fields['ds_y'], ''):
            raise plugins.DatasetPluginException(
                'Input and output datasets cannot be the same.')
        # make a new dataset with name in fields['ds_out']
        #self.ds_out = plugins.Dataset1D(fields['ds_out'])
        self.ds_out = MisuraPluginDataset1D(fields['ds_out'])
        self.ds_out.unit = '-'
        self.ds_out.old_unit = '-'
        # return list of datasets
        return [self.ds_out]

    def updateDatasets(self, fields, helper):
        """Calculate coefficient
        """
        smooth = fields['smooth']
        recon = fields['reconfigure']
        smode = fields['smode']
        start = fields['start']
        initial_dimension = fields['percent']

        xds = helper._doc.data[fields['ds_x']]
        yds = helper.getDataset(fields['ds_y'])
        _yds = helper._doc.data.get(fields['ds_y'])
        x = xds.data
        y = yds.data

        # Remove/guess initial_dimension if an m_percent flag exists
        if not getattr(_yds, 'm_percent', True):
            initial_dimension = getattr(_yds, 'm_initialDimension', initial_dimension)
        elif getattr(_yds, 'm_percent', None) is True:
            initial_dimension = 0
            
        i = np.where(x > start)[0][0]
        j = None
        
        # Define the end of calc
        j = np.where(x == x.max())[0][0]
        ymax = y[j]
        xmax = x[j]

        # Smooth input curves
        if smooth > 0:
            if smode != 'Output':
                y[i:j] = SmoothDatasetPlugin.smooth(y[i:j], smooth, 'hanning')
            if smode == 'X and Y':
                x[i:j] = SmoothDatasetPlugin.smooth(x[i:j], smooth, 'hanning')

        xstart = start
        d = 15
        pre = max((0, i-d))
        post = min(i+d, len(y)-1)
        ystart = y[pre:post].mean() or 1

        out = calculate_coefficient(x, y, xstart, ystart, initial_dimension, 
                                    getattr(_yds, 'm_percent', False), 
                                    linearize=fields.get('linearize', 0))
        out[:i+d] = np.nan

        # TODO: multiple ramps
        # Detect the maximum temperature
        # and start a new coefficient point
        if recon == 'Stop':
            out[j:] = np.nan
        else:
            restart_index = np.where(x == x.max())[0][0]

            out[restart_index:] = calculate_coefficient(x[restart_index:], y[restart_index:],
                                                             x[restart_index],  y[restart_index],
                                                             initial_dimension, getattr(_yds, 'm_percent', False))
            out[restart_index:][x[restart_index:] > x[restart_index] - 1] = np.nan
        # Apply factor
        out /= fields.get('factor', 1.)
        # Smooth output curve
        if smooth > 0 and smode == 'Output':
            out[i:j] = SmoothDatasetPlugin.smooth(out[i:j], smooth, 'hanning')
        self.ds_out.update(data=out)
        u = xds.attr.get('unit', False)
        u = '-' if not u else '1/'+u
        self.ds_out.unit = u
        self.ds_out.old_unit = u
        return [self.ds_out]

def calculate_coefficient(x_dataset, y_dataset, x_start, y_start, 
                          initial_dimension, is_percent, linearize=0):
    denominator = initial_dimension or 100.
    if not initial_dimension:
        is_percent = True
    if not is_percent:
        denominator = (initial_dimension + y_start)

    out =  (y_dataset - y_start) / (x_dataset - x_start) / denominator
    if not linearize:
        return out
    linearize = int(min((linearize, len(out)/4.)))
    end = min(3*linearize, len(out)/2.)
    post = out[linearize:end]
    factors, res, rank, sing, rcond = np.polyfit(np.arange(len(post))+linearize, post, deg=1, full=True)
    func = np.poly1d(factors)
    pre = func(np.arange(linearize))
    out[:linearize] = pre
    return out
    


# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(CoefficientPlugin)
