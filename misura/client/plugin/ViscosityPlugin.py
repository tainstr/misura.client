#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Viscosity according to the VFT equation"""
from misura.canon.logger import Log as logging
import veusz.plugins as plugins
import numpy as np

# Known points
methods = ('Glass transition DIL (10^13 Poises)',
           'Softening point DIL MEC (10^10.25 Poises)',
           'Sintering beginning HSM powders (10^10 Poises)',
           'Softening HSM & Softening DIL OPT (10^8.2 Poises)',
           'Sphere HSM (10^6.1 Poises)',
           'Half Sphere HSM (10^4.55 Poises)',
           )
values = (10 ** 13,
          10 ** 10.25,
          10 ** 10,
          10 ** 8.2,
          10 ** 6.1,
          10 ** 4.55)


def getViscosity(entry):
    if entry in methods:
        i = methods.index(entry)
        r = values[i]
    else:
        r = float(entry)
    return r


def viscosity_calc(temperatures, known_temperatures, known_viscosities):
    T1, T2, T3 = known_temperatures
    V1, V2, V3 = known_viscosities
    # Solve VFT
    g1 = V1 * T1
    g2 = V2 * T2
    g3 = V3 * T3

    ratio = (T3 - T1) / (T2 - T1)
    T0 = g1 - g3 + ((g2 - g1) * ratio)
    T0 = T0 / ((V1 - V3) - ((V1 - V2) * ratio))

    A = (g2 - g1 + ((V1 - V2) * T0)) / (T2 - T1)
    B = (T1 - T0) * (V1 - A)

    print 'VFT', A, B, T0
    # Apply VFT
    output = A + B / (temperatures - T0)
    canc=np.where(temperatures < T0+1)[0]
    print 'Cancelling',T0, min(temperatures), max(temperatures), canc, temperatures
    if len(canc):
        output[canc] = 0
    return output


class ViscosityPlugin(plugins.DatasetPlugin):

    """Dataset plugin to smooth data values"""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Viscosity')
    # internal name for reusing plugin later
    name = 'Viscosity'
    # string which appears in status bar
    description_short = 'Viscosity'

    # string goes in dialog box
    description_full = ('Viscosity VFT'
                        'Viscosity VFT')

    def __init__(self, ds_in='', T1=0, V1=0, T2=0, V2=0, T3=0, V3=0, ds_out=''):
        """Define input fields for plugin."""
        self.fields = [
            plugins.FieldDataset(
                'ds_in', 'Temperature dataset', default=ds_in),
            plugins.FieldFloat('T1', 'First temperature value', default=T1),
            plugins.FieldCombo(
                'V1', 'First known viscosity value', default=V1, items=methods, editable=True),

            plugins.FieldFloat('T2', 'Second temperature value', default=T2),
            plugins.FieldCombo(
                'V2', 'Second known viscosity value', default=V2, items=methods, editable=True),

            plugins.FieldFloat('T3', 'Third temperature value', default=T3),
            plugins.FieldCombo(
                'V3', 'Third known viscosity value', default=V3, items=methods, editable=True),

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
        logging.debug('%s %s', 'DSOUT', fields)
        self.ds_out = plugins.Dataset1D(fields['ds_out'])
        self.ds_out.unit = 'poise'

        # return list of datasets
        return [self.ds_out]

    def updateDatasets(self, fields, helper):
        """Calculate the viscosity dataset.
        This function should *update* the dataset(s) returned by getDatasets
        """
        # get the input dataset - helper provides methods for getting other
        # datasets from Veusz
        ds_in = helper.getDataset(fields['ds_in'])
        T = np.array(ds_in.data)
        V1 = getViscosity(fields['V1'])
        V2 = getViscosity(fields['V2'])
        V3 = getViscosity(fields['V3'])

        output = viscosity_calc(T, 
                    [fields['T1'],fields['T2'],fields['T3']], 
                    [V1,V2,V3])
        
        self.ds_out.update(data=output)
        self.ds_out.unit = 'poise'
        return [self.ds_out]

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(ViscosityPlugin)
