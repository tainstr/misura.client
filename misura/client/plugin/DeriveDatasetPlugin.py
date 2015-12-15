#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Derive a dataset."""
import veusz.plugins as plugins
import numpy as np
from utils import derive, xyderive, smooth

class DeriveDatasetPlugin(plugins.DatasetPlugin):

    """Dataset plugin to derive curves"""
    # tuple of strings to build position on menu
    menu = ('Compute', 'Derivatives')
    # internal name for reusing plugin later
    name = 'Derive'
    # string which appears in status bar
    description_short = 'Compute point-by-point derivative'

    # string goes in dialog box
    description_full = ('Compute point-by-point derivative, dX/dY'
                        'If no Y dataset is defined, than the (difference between order points)/order is returned.'
                        'The last/starting order values are repeated in order to obtain an output dataset of the same length.')

    def __init__(self, ds_x='', ds_y='', order=1, method='Middle', smooth=5, ds_out=''):
        """Define input fields for plugin."""
        self.fields = [
            plugins.FieldDataset(
                'ds_y', 'Dataset to be derived (Y)', default=ds_y),
            plugins.FieldDataset('ds_x', 'Dataset X', default=ds_x),
            plugins.FieldInt('order', 'Order of derivation', default=order),
            plugins.FieldCombo('method', 'Derivative method', default=method, items=(
                'Middle', 'Right', 'Left'), editable=False),
            plugins.FieldInt('smooth', 'Smoothing Window', default=smooth),
            plugins.FieldDataset(
                'ds_out', 'Output dataset name', default=ds_out)
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
        self.ds_out = plugins.Dataset1D(fields['ds_out'])
        # return list of datasets
        return [self.ds_out]

    def updateDatasets(self, fields, helper):
        """	This function should *update* the dataset(s) returned by getDatasets
        """
        # get the input dataset - helper provides methods for getting other
        # datasets from Veusz
        ds_y = np.array(helper.getDataset(fields['ds_y']).data)
        # get the value to add
        order = fields['order']
        method = fields['method']
        smooth_num = fields['smooth']
        ds_x = None
        if smooth_num > 0:
            ds_y = smooth(ds_y, smooth_num, 'hanning')
        if fields['ds_x'] != '':
            # Derive with respect to X
            ds_x = np.array(helper.getDataset(fields['ds_x']).data)
            if smooth_num > 0:
                ds_x = smooth(ds_x, smooth_num, 'hanning')
            out = xyderive(ds_x, ds_y, order, method)
        else:
            # Derive with respect to point indexes
            out = derive(ds_y, method, order)

        self.ds_out.update(data=out)
        return [self.ds_out]

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(DeriveDatasetPlugin)
