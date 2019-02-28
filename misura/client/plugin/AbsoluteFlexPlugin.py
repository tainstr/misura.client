#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import veusz.plugins as plugins
import veusz.document as document
import numpy as np
import SmoothDatasetPlugin
from utils import MisuraPluginDataset1D
from misura.canon.circle import absolute_flex
from . import utils
from misura.canon.logger import get_module_logging
logging = get_module_logging(__file__)

class AbsoluteFlexPlugin(utils.CachedResultFragment, plugins.DatasetPlugin):

    """Re-calculate Absolute Fleximeter displacement from calibration factors and thrre-point displacements"""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Absolute Flex')
    # internal name for reusing plugin later
    name = 'AbsoluteFlex'
    # string which appears in status bar
    description_short = 'Absolute Fleximeter'

    # string goes in dialog box
    description_full = (
        'Re-calculate Absolute Fleximeter displacement from calibration factors and thrre-point displacements')
    
    cached_dataset_fields = ['ds_middle','ds_right','ds_left']

    def __init__(self, ds_middle='', ds_right='', ds_left='', right_calibration=35000., 
                 left_calibration=35000., percent=0., smooth=5, smode='Output',ds_out='absflex', ds_radius='absradius'):
        """Define input fields for plugin."""
        self.fields = [
            plugins.FieldDataset('ds_middle', 'Center displacement', default=ds_middle),
            plugins.FieldDataset('ds_right', 'Right displacment', default=ds_right),
            plugins.FieldDataset('ds_left', 'Left displacment', default=ds_left),
            
            plugins.FieldFloat('right_calibration', '', default=right_calibration),
            plugins.FieldFloat('left_calibration', '', default=left_calibration),
            
            plugins.FieldInt('smooth', 'Smoothing Window', default=smooth),
            plugins.FieldCombo('smode', descr='Apply Smoothing to', items=[
                               'Input', 'Output'], default=smode),
            plugins.FieldDataset(
                'ds_out', 'Output displacement name', default=ds_out),
            plugins.FieldDataset(
                'ds_radius', 'Output radius name', default=ds_radius),
        ]

    def getDatasets(self, fields):
        """Returns single output dataset (self.ds_out).
        This method should return a list of Dataset objects, which can include
        Dataset1D, Dataset2D and DatasetText
        """
        # raise DatasetPluginException if there are errors
        ds = set([fields['ds_middle'], fields['ds_right'], fields['ds_left'], 
                  fields['ds_out'], fields['ds_radius']])
        if len(ds)<5:
            raise plugins.DatasetPluginException(
                'All input/output datasets must differ.')
        if '' in ds:
            raise plugins.DatasetPluginException(
                'All input/output dataset fields must be initialized.')
        self.ds_out = MisuraPluginDataset1D(fields['ds_out'])
        self.ds_out.unit = 'micron'
        self.ds_out.old_unit = 'micron'
        self.ds_radius = MisuraPluginDataset1D(fields['ds_radius'])
        self.ds_radius.unit = 'micron'
        self.ds_radius.old_unit = 'micron'
        # return list of datasets
        return [self.ds_out, self.ds_radius]
    
    def calculate_absolute_flex(self):
        smooth = self.cached_fields['smooth']
        smode = self.cached_fields['smode']
        
        M = self.cached_datasets['ds_middle']
        R = self.cached_datasets['ds_right']
        L = self.cached_datasets['ds_left']
        
        # Smooth input curves
        if smooth > 0 and smode == 'Input':
            M = SmoothDatasetPlugin.smooth(M, smooth, 'hanning')
            R = SmoothDatasetPlugin.smooth(R, smooth, 'hanning')
            L = SmoothDatasetPlugin.smooth(L, smooth, 'hanning')
        
        #TODO: convert to array math
        out = []
        rad = []
        Rcal = self.cached_fields['right_calibration']
        Lcal = self.cached_fields['left_calibration']
        for i in xrange(len(M)):
            res = absolute_flex(M[i],R[i],L[i], Rcal, Lcal)
            out.append(res['d'])
            rad.append(res['radius'])
        
        out = np.array(out)
        rad = np.array(rad)
            
        # Smooth output curve
        if smooth > 0 and smode == 'Output':
            out = SmoothDatasetPlugin.smooth(out, smooth, 'hanning')
            rad = SmoothDatasetPlugin.smooth(rad, smooth, 'hanning')
            
        return out,rad
            
    
    def updateDatasets(self, fields, helper):
        """Calculate coefficient
        """
        if self.is_cache_dirty(fields, helper):
            out, rad = self.calculate_absolute_flex()
            self.cached_result = [out,rad]
        else:
            out,rad = self.cached_result

        self.ds_out.update(data=out)
        self.ds_radius.update(data=rad)
        return [self.ds_out]

    


# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(AbsoluteFlexPlugin)
