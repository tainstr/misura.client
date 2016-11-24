#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing SurfaceTensionPlugin.py plugin."""
import unittest
from misura.canon.logger import Log as logging

from misura.client.tests import iutils_testing as iut
from misura.client.plugin import SurfaceTensionPlugin
from misura.client.plugin.SurfaceTensionPlugin import DensityFunction

import numpy as np


import veusz.document as document
import veusz.datasets as datasets
import veusz.plugins

from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)


def setUpModule():
    logging.debug('%s %s', 'setUpModule', __name__)


def tearDownModule():
    logging.debug('%s %s', 'tearDownModule', __name__)


def insertData(doc, datadict):
    for key, data in datadict.iteritems():
        ds = datasets.Dataset(data)
        doc.setData(key, ds)

#@unittest.skip('')


class TestSurfaceTensionPlugin(unittest.TestCase):

    """Tests the SurfaceTensionPlugin."""

    fields = {'rho0': 1000, 'T0': 25, 'ex_start': 0, 'ex_end': 0, 'dim': 'Linear',
              'grho0': 1.18, 'gT0': 25, 'gdim': 'Volumetric',
              'ds_out': 'out'}

    def do(self, beta, R0, T, dil='', dilT='', gdil='', gdilT='', **kw):
        fields = self.fields.copy()
        doc = document.Document()
        p = self.create_plugin(doc, fields, beta, R0, T, dil='', dilT='', gdil='', gdilT='', **kw)

        logging.debug('%s', 'get ds')
        p.getDatasets(fields)
        logging.debug('%s', 'update ds')
        out = p.updateDatasets(fields, veusz.plugins.DatasetPluginHelper(doc))
        return out

    def create_plugin(self, doc, fields, beta, R0, T, dil='', dilT='', gdil='', gdilT='', **kw):

        ds = {'beta': beta, 'R0': R0, 'T': T, 'dil': dil,
              'dilT': dilT, 'gdil': gdil, 'gdilT': gdilT}
        for k in ds.keys():
            if ds[k] == '':
                fields[k] = ''
                continue
            logging.debug('%s %s', 'inserting data', k)
            insertData(doc, {k: ds[k]})
            fields[k] = k
        fields.update(kw)
        fields['ds_out'] = 'out'
        logging.debug('%s', 'build op')
        return SurfaceTensionPlugin(**fields)

    def test_infnan(self):
        """Check tolerance towards nan/inf"""
        N = 10
        beta = np.ones(N)
        R0 = np.ones(N)
        beta[-1] = 0  # induce divide by zero (inf)
        R0[-2] = 0
        beta[-2] = 0  # induce nan
        T = np.arange(25, 25 + N)
        out = self.do(beta, R0, T)
        self.assertEqual(len(out), N)
        # Both nan and inf should be converted to zero
        self.assertEqual(out[-1], 0)
        self.assertEqual(out[-2], 0)
        logging.debug('%s', out)

    def test_water(self):
        """Filled with water test data"""
        N = 10
        beta = np.ones(N) * 4.3
        R0 = np.ones(N) * 6220
        T = np.ones(N) * 25
        out = self.do(beta, R0, T)
        self.assertEqual(len(out), N)
        logging.debug('%s %s', 'water', out)

    def test_when_temperature_changes_too_little_sample_expansion_and_sample_expansion_temperature_are_empty(self):
        """
           If temperature changes too little, it becomes impossible to
           interpolate data to calculate density variations.
           So, no variation is assumed.
        """
        N = 100
        beta = np.ones(N) * 4.3
        R0 = np.ones(N) * 6220
        fixed_temperature = np.ones(N) * 25

        fields = self.fields.copy()
        doc = document.Document()

        plugin = self.create_plugin(doc, fields, beta, R0, fixed_temperature)

        #sample expansion is 'dil'
        #sample expansion temperature is 'dilT'
        for actual_default_value in [field for field in plugin.fields if field.name.startswith("dil")]:
            self.assertEqual('', actual_default_value.default)



class TestDensityFunction(unittest.TestCase):
    def test_basic_interpolation_and_extrapolation(self):
        density_function = DensityFunction(1000, 25, [0, 0.1, 0.2, 0.3, 0.4], [25, 26, 27, 28, 29], 28, 29)

        self.assertEqual(1000, density_function(25))
        self.assertGreater(density_function(22), 1000)
        self.assertLess(density_function(25.5), 1000)
        self.assertLess(density_function(30), 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
