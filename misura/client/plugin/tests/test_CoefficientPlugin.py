#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing CoefficientPlugin."""
import unittest
from misura.canon.logger import Log as logging

from misura.client.tests import iutils_testing as iut
from misura.client.plugin import CoefficientPlugin
import numpy as np


import veusz.document as document
import veusz.plugins

from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)


def setUpModule():
    logging.debug('%s %s', 'setUpModule', __name__)


def tearDownModule():
    logging.debug('%s %s', 'tearDownModule', __name__)


def insertData(doc, datadict):
    for key, data in datadict.iteritems():
        ds = document.Dataset(data)
        doc.setData(key, ds)

# @unittest.skip('')


class TestCurveOperationPlugin(unittest.TestCase):

    """Tests the CurveOperationPlugin."""

    def do(self, ds_x, ds_y, start=50., percent=0., reconfigure='Continue', smooth=5, smode='X and Y', ds_out='coeff'):
        doc = document.Document()
        insertData(doc, {'ds_x': ds_x, 'ds_y': ds_y})
        fields = {'ds_x': 'ds_x', 'ds_y': 'ds_y', 'start':start, 'percent':percent, 'reconfigure': reconfigure, 'smooth': smooth, 'smode':smode, 'ds_out': ds_out}
        p = CoefficientPlugin(**fields)
        p.getDatasets(fields)
        out = p.updateDatasets(fields, veusz.plugins.DatasetPluginHelper(doc))
        return out


    def test(self):
        """Test the operation from a Misura3 file"""
        x = np.linspace(0, 1000, 1001)
        inidim = 10000
        teor = 10 ** -3
        y = x * teor * inidim
        yp = y / inidim
        
        print x[50], y[50]
        out = self.do(x, y)[0].data
        self.assertTrue((out[:51] == np.zeros(51)).all())
        
        print out[51:100]
        
        print 'ABOLUTE'
        print x[50], yp[50]
        out = self.do(x, yp, percent=inidim)[0].data
        self.assertTrue((out[:51] == np.zeros(51)).all())
        
        print out[51:100]       
        
        



if __name__ == "__main__":
    unittest.main(verbosity=2)
