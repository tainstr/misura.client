#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing CoefficientPlugin."""
import unittest
from misura.canon.logger import Log as logging

from misura.client.tests import iutils_testing as iut
from misura.client.plugin import CoefficientPlugin
import numpy as np


import veusz.document as document
import veusz.datasets as datasets
import veusz.plugins


logging.debug('%s %s', 'Importing', __name__)


def setUpModule():
    logging.debug('%s %s', 'setUpModule', __name__)


def tearDownModule():
    logging.debug('%s %s', 'tearDownModule', __name__)


def insertData(doc, datadict):
    for key, data in datadict.iteritems():
        ds = datasets.Dataset(data)
        doc.setData(key, ds)

# @unittest.skip('')


class TestCurveOperationPlugin(unittest.TestCase):

    """Tests the CurveOperationPlugin."""
    
    set_y_percent = False
    
    def do(self, ds_x, ds_y, start=50., percent=0., reconfigure='Continue', smooth=5, smode='X and Y', ds_out='coeff'):
        doc = document.Document()
        insertData(doc, {'ds_x': ds_x, 'ds_y': ds_y})
        ds = doc.data['ds_y']
        ds.m_percent = self.set_y_percent
        doc.setData('ds_y', ds)
        fields = {'ds_x': 'ds_x', 'ds_y': 'ds_y', 'start':start, 'percent':percent, 'reconfigure': reconfigure, 'smooth': smooth, 'smode':smode, 'ds_out': ds_out}
        p = CoefficientPlugin(**fields)
        p.getDatasets(fields)
        out = p.updateDatasets(fields, veusz.plugins.DatasetPluginHelper(doc))
        return out


    def test(self):
        """Coefficient for a straight line"""
        x = np.linspace(0, 1000, 1001)
        inidim = 10000
        teor = 10 ** -4
        # Absolute expansion
        y = x * teor * inidim
        # Percent expansion
        yp = 100 * y / inidim
        
        out = self.do(x, y, percent=inidim)[0].data
        print out
        self.assertTrue(np.isnan(out[:51]).all())
        
        self.set_y_percent = True
        out = self.do(x, yp, percent=inidim)[0].data
        self.assertTrue(np.isnan(out[:52]).all())
        delta = teor*10**-8
        self.assertAlmostEqual(out[52:-1].std(), 0, delta = delta*10**-2)
        self.assertAlmostEqual(out[52:-1].mean(), teor, delta = delta)
        
        



if __name__ == "__main__":
    unittest.main(verbosity=2)
