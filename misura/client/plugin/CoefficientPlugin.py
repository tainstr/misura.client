#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import veusz.plugins as plugins
import veusz.document as document
import numpy
import SmoothDatasetPlugin


class CoefficientPlugin(plugins.DatasetPlugin):

    """Calculate a coefficient"""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Coefficient')
    # internal name for reusing plugin later
    name = 'Coefficient'
    # string which appears in status bar
    description_short = 'Calculate coefficient'

    # string goes in dialog box
    description_full = ('Calculate a coefficient')

    def __init__(self, ds_x='', ds_y='', start=50., percent=0., reconfigure='Continue', smooth=5, smode='X and Y', ds_out='coeff'):
        """Define input fields for plugin."""
        self.fields = [
            plugins.FieldDataset('ds_x', 'X Dataset', default=ds_x),
            plugins.FieldDataset('ds_y', 'Y Dataset', default=ds_y),
            plugins.FieldFloat('start', 'Starting X value', default=start),
            plugins.FieldFloat(
                'percent', descr='From percentile factor', default=percent),
            plugins.FieldCombo('reconfigure', descr='When cooling is found', items=[
                               'Continue', 'Restart', 'Stop'], default=reconfigure),
            plugins.FieldInt('smooth', 'Smoothing Window', default=smooth),
            plugins.FieldCombo('smode', descr='Apply Smoothing to', items=[
                               'X and Y', 'Y alone', 'Output'], default=smode),
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
        self.ds_out = plugins.Dataset1D(fields['ds_out'])
        # return list of datasets
        return [self.ds_out]

    def updateDatasets(self, fields, helper):
        """Calculate coefficient
        """
        smooth = fields['smooth']
        recon = fields['reconfigure']
        smode = fields['smode']
        start = fields['start']
        percent = fields['percent']

        xds = helper.getDataset(fields['ds_x'])
        yds = helper.getDataset(fields['ds_y'])
        x = xds.data
        y = yds.data
        # If percent, convert to absolute
        if percent != 0. and getattr(yds, 'm_percent', False):
            y *= percent / 100.
        # Search the beginning of the coefficient
        chk = numpy.abs(x - start)
        i = numpy.where(chk == min(chk))[0][0]
        j = None
        # Define the end of calc
        if recon != 'Continue':
            j = numpy.where(x == x.max())[0][0]
            ymax = y[j]
            xmax = x[j]
        # Smooth input curves
        if smooth > 0:
            if smode != 'Output':
                y[i:j] = SmoothDatasetPlugin.smooth(y[i:j], smooth, 'hanning')
            if smode == 'X and Y':
                x[i:j] = SmoothDatasetPlugin.smooth(x[i:j], smooth, 'hanning')

        xstart = x[i]
        ystart = y[i]
        # COEFFICIENT
        out = (y - ystart) / (x - xstart) / (percent + ystart)
        out[:i + 1] = 0
        # TODO: multiple ramps
        # Detect the maximum temperature
        # and start a new coefficient point
        if recon == 'Stop':
            out[j:] = 0.
        elif recon == 'Restart':
            out[j:] = (y[j:] - ymax) / (x[j:] - xmax) / (percent + ymax)
        # Smooth output curve
        if smooth > 0 and smode == 'Output':
            out[i:j] = SmoothDatasetPlugin.smooth(out[i:j], smooth, 'hanning')
        self.ds_out.update(data=out)
        return [self.ds_out]


# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(CoefficientPlugin)
