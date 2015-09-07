#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Surface tension from capillarity shape and scale parameters and expansion data."""
from misura.canon.logger import Log as logging
import veusz.plugins as plugins
import numpy as np
from scipy import interpolate


class DensityFunction(object):

    """Callable returning density at any temperature, given a reference density and temperature and linear/volumetric expansion curves"""

    def __init__(self, rho0, T0, dil=False, T=False, ex_start=0, ex_end=0, dim='Linear'):
        logging.debug('%s %s %s %s %s %s %s %s', 'DensityFunction',
                      rho0, T0, dil, T, ex_start, ex_end, dim)
        self.rho0 = rho0
        self.T0 = T0
        self.dil = dil
        self.T = T
        self.dim = dim
        if dil is False or T is False:
            self.f = False
            return
        # Set up expansion curve
        self.f = interpolate.interp1d(T, dil)

        # Extrapolation towards lower T
        minT = min(T)
        self.low_start = minT + min(3, minT * 3 // 100)
        self.low_end = minT + min(10, minT // 10)
        self.low_dil = self.f(self.low_start)
        low_e2 = self.f(self.low_end)
        self.low_coef = (low_e2 - self.low_dil) / \
            (self.low_end - self.low_start)
        # Reference expansion
        if T0 < self.low_start:
            # extrapolate towards lower start temperature
            dT = (self.low_start - T0)
            self.e0 = self.low_dil - dT * self.low_coef
        else:
            self.e0 = self.f(T0)
        # Extrapolation
        self.ex_end = ex_end
        self.ex_start = ex_start
        if ex_end <= 0:
            return
        # Real expansion at end of extrapolation interval
        self.ex_dil = self.f(ex_end)
        # Fixed coefficient for any dilatation above ex_end
        self.ex_coef = (self.ex_dil - self.f(ex_start)) / (ex_end - ex_start)

    def __call__(self, T):
        """Adapt density to volumetric expansion"""
        if self.f is False:
            # If T was an array, return an array of rho0:
            return (T * 0) + self.rho0

        def func(T):
            # Use extrapolation
            if self.ex_end > 0 and T > self.ex_end:
                e = self.ex_dil - self.e0 + (T - self.ex_end) * self.ex_dil
            elif T < self.low_start:
                e = self.low_dil - (self.low_start - T) * self.low_coef
            else:
                # Use interpolated function
                e = self.f(T) - self.e0
            # Adapt linear to volumetric
            if self.dim == 'Linear':
                e = (1 + e / 100) ** 3
                return self.rho0 / e
            # Already volumetric
            rho = self.rho0 * 100 / (100 + e)
        vfunc = np.vectorize(func)
        rho = vfunc(T)
        return rho


def air_density(T):
    # Source:
    # http://bouteloup.pierre.free.fr/lica/phythe/don/air/air_density_plot.pdf
    return 360.77819 * ((T + 273.15) ** -1.00336)

g = 9.80665


class SurfaceTensionPlugin(plugins.DatasetPlugin):

    """Dataset plugin to perform operations between couples of x,y datasets."""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Surface Tension')
    # internal name for reusing plugin later
    name = 'SurfaceTension'
    # string which appears in status bar
    description_short = 'Calculate surface tension from runtime capillary parameters.'

    # string goes in dialog box
    description_full = ('Calculate surface tension from capillary shape parameters,'
                        'scaling factor, temperature,'
                        'sample expansion curve, media expansion curve.')

    MIN_TEMPERATURE_VARIATION = 100

    def __init__(self, beta='', R0='', T='', rho0=1000, T0=25, dil='', dilT='', ex_start=0, ex_end=0, dim='Linear',
                            grho0=air_density(25), gT0=25, gdil='', gdilT='', gdim='Volumetric', ds_out='', temperature_dataset=[0, MIN_TEMPERATURE_VARIATION]):
        """Define input fields for plugin."""

        default_sample_expansion = dil
        default_sample_expansion_temperature = dilT

        if max(temperature_dataset) - min(temperature_dataset) < self.MIN_TEMPERATURE_VARIATION:
            default_sample_expansion = ''
            default_sample_expansion_temperature = ''

        self.fields = [
            plugins.FieldDataset(
                'beta', 'Capillarity factor dataset', default=beta),
            plugins.FieldDataset('R0', 'Scaling factor dataset', default=R0),
            plugins.FieldDataset(
                'T', u'Sample temperature (\u00B0C)', default=T),

            plugins.FieldFloat(
                "rho0", descr=u"Reference sample density (kg/m\u00B3)", default=rho0),
            plugins.FieldFloat(
                "T0", descr=u"Reference sample temperature (\u00B0C)", default=T0),
            plugins.FieldDataset(
                'dil', 'Sample expansion [blank=fixed] (%)', default=default_sample_expansion),
            plugins.FieldDataset(
                'dilT', u'Sample expansion temperature [blank=as beta] (\u00B0C)', default=default_sample_expansion_temperature),
            plugins.FieldFloat(
                'ex_start', u'Extrapolate from temperature [0=no] (\u00B0C)', default=ex_start),
            plugins.FieldFloat(
                'ex_end', u'Extrapolate to temperature [0=no] (\u00B0C)', default=ex_end),

            plugins.FieldCombo("dim", descr="Sample expansion dimension", items=[
                               'Linear', 'Volumetric'], default=dim),

            plugins.FieldFloat(
                "grho0", descr=u"Reference gas density (kg/m\u00B3)", default=grho0),
            plugins.FieldFloat(
                "gT0", descr=u"Reference gas temperature (\u00B0C)", default=gT0),

            plugins.FieldDataset(
                'gdil', 'Gas expansion [blank=air] (%)', default=gdil),
            plugins.FieldDataset(
                'gdilT', 'Gas expansion temperature [blank=air] (%)', default=gdilT),

            plugins.FieldCombo("gdim", descr="Gas expansion dimension", items=[
                               'Linear', 'Volumetric'], default=gdim),

            plugins.FieldDataset(
                'ds_out', 'Output dataset name', default=ds_out)
        ]
        self.error = 0

    def getDatasets(self, fields):
        """Returns single output dataset (self.ds_out).
        This method should return a list of Dataset objects, which can include
        Dataset1D, Dataset2D and DatasetText
        """
        # raise DatasetPluginException if there are errors
        if len(set([fields['beta'], fields['R0'], fields['T']])) < 3:
            raise plugins.DatasetPluginException(
                'Capillarity, scaling and temperature datasets must differ.')
        if fields['ds_out'] in set([fields['beta'], fields['R0'], fields['T'], '', fields['dil'], fields['dilT'], fields['gdil'], fields['gdilT']]):
            raise plugins.DatasetPluginException(
                'Input and output datasets cannot be the same.')
        # make a new dataset with name in fields['ds_out']
        self.ds_out = plugins.Dataset1D(fields['ds_out'])
        self.error = 0
        # return list of datasets
        return [self.ds_out]

    def updateDatasets(self, fields, helper):
        # Capillarity data
        beta = np.array(helper.getDataset(fields['beta']).data)
        R0 = np.array(helper.getDataset(fields['R0']).data)
        # Sample expansion data
        rho0 = fields['rho0']
        T0 = fields['T0']
        dsample = None
        if fields['T'] == '':
            T = np.ones(len(beta)) * T0
            dsample = np.ones(len(beta)) * rho0
        else:
            T = np.array(helper.getDataset(fields['T']).data)
        if len(set([len(beta), len(R0), len(T)])) > 1:
            raise plugins.DatasetPluginException(
                'Sample datasets must have same length')

        dim = fields['dim']
        ex_start = fields['ex_start']
        ex_end = fields['ex_end']
        # Disable if one is 0 or negative
        if ex_start * ex_end <= 0:
            ex_start, ex_end = 0, 0
        if fields['dil'] == '':
            dil = False
            dilT = False
        else:
            dil = np.array(helper.getDataset(fields['dil']).data)
            # Use the same T array
            if fields['dilT'] == '':
                dilT = T
            else:
                dilT = np.array(helper.getDataset(fields['dilT']).data)
            if len(dil) != len(dilT):
                raise plugins.DatasetPluginException(
                    'Sample expansion/T datasets must have same length')

        # Gas expansion data
        grho0 = fields['grho0']
        gT0 = fields['gT0']
        gdim = fields['gdim']
        if fields['gdil'] == '':
            gdil, gdilT = False, False
        else:
            gdil = np.array(helper.getDataset(fields['gdil']).data)
            gdilT = np.array(helper.getDataset(fields['gdilT']).data)
            if len(dil) != len(dilT):
                raise plugins.DatasetPluginException(
                    'Gas expansion/T datasets must have same length')

        # Correct dil curves starting at 100%
        if dil is not False:
            if dil[0] > 50:
                dil -= 100

        # Sample density vector
        if dsample is None:
            df = DensityFunction(rho0, T0, dil, dilT, ex_start, ex_end, dim)
            dsample = df(T)
        # Gas density vector
        if not gdil:
            gdf = air_density
        else:
            gdf = DensityFunction(grho0, gT0, gdil, gdilT, dim=gdim)
        dgas = gdf(T)
        # Surface tension formula
        gamma = g * (dsample - dgas) * ((R0 / 1e6) ** 2) / (beta / 1000)
        # Remove nan/inf due to missing betas (beta=0)
        gamma[np.isnan(gamma) + np.isinf(gamma)] = 0
        self.ds_out.update(data=gamma)
        return gamma

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(SurfaceTensionPlugin)
