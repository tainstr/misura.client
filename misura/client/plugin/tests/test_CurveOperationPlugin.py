#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing plugin/CurveOperationPlugin.py plugin."""
import unittest
from misura.canon.logger import Log as logging

from misura.client.tests import iutils_testing as iut
from misura.client.plugin import CurveOperationPlugin
from misura.client.plugin.CurveOperationPlugin import curve_operation
import numpy as np


import veusz.document as document
import veusz.datasets as datasets
import veusz.plugins

logging.debug('Importing', __name__)


def setUpModule():
    logging.debug('setUpModule', __name__)


def tearDownModule():
    logging.debug('tearDownModule', __name__)


def insertData(doc, datadict):
    for key, data in datadict.iteritems():
        ds = datasets.Dataset(data)
        doc.setData(key, ds)



class TestCurveOperationPlugin(unittest.TestCase):

    """Tests the CurveOperationPlugin."""

    def do(self, ax, ay, bx, by, op='A-B', err=1e-10, **kw):
        doc = document.Document()
        insertData(doc, {'ax': ax, 'ay': ay, 'bx': bx, 'by': by})
        fields = {'ax': 'ax', 'ay': 'ay', 'bx': 'bx', 'by': 'by', 'ds_out': 'out',
                  'operation': op, 'smooth': False, 'relative': True, 'tolerance': 1.}
        fields.update(kw)
        p = CurveOperationPlugin(**fields)
        p.getDatasets(fields)
        out = p.updateDatasets(fields, veusz.plugins.DatasetPluginHelper(doc))
        self.assertLess(p.error, err)
        return out

    
    def test_sampling(self):
        """Test the operation from a Misura3 file"""
        # Two equal datasets, but with different sampling
        ax = np.linspace(0, 10, 10)
        ay = ax[:]
        # B is supersampled by 10
        bx = np.linspace(0, 10, 100)
        by = bx[:]
        # SUPERSAMPLING
        # Subtract B to A
        sup = self.do(ax, ay, bx, by, 'A-B')
        logging.debug('Supersampling', sup.sum())
        # Output value should have same length of ref. array, A
        self.assertEqual(len(sup), len(ay))

        # UNDERSAMPLING
        und = self.do(bx, by, ax, ay, 'A-B')
        logging.debug('Undersampling', und.sum())
        # Output value should have same length of ref. array, B
        self.assertEqual(len(und), len(by))
        self.assertAlmostEqual(sup.sum(), 0)
        self.assertAlmostEqual(und.sum(), 0)


    def test_shifting(self):
        """Test operations between shifted datasets"""
        ax = np.linspace(0, 10, 10)
        ay = ax[:]
        # B entirely comprises A. Moreover, it is supersampled.
        bx = np.linspace(0, 15, 100)
        by = np.linspace(-4, 11, 100)
        out = self.do(ax, ay, bx, by, 'A-B', relative=True)
        self.assertAlmostEqual(out.sum() / len(ax), 0, delta=1)
        # What happens if B is smaller than A? ---> extrapolation?
    
    def test_cycling(self):
        """Test operations between non-univocal curves"""
        ax = np.linspace(0, 20, 200)
        # Temperature raises and goes down (2 ramps)
        ay = np.concatenate((np.linspace(0, 100, 100),
                             np.linspace(100, 0, 100)))

        # Supersampled and longer version of A, comprising 2 increasing and 2
        # decreasing ramps
        bx = np.linspace(0, 40, 4000)
        by = np.concatenate((np.linspace(0, 100, 1000),
                             np.linspace(100, 0, 1000),
                             np.linspace(0, 100, 1000),
                             np.linspace(100, 0, 1000)
                             ))
        
        out = self.do(ax, ay, bx, by, 'A-B', err=18)
        self.assertAlmostEqual(out.sum() / len(ax), 0, delta=1)


    def test_non_uniform(self):
        ax = np.linspace(0, 40, 200)
        # Temperature raises and goes down (2 ramps)
        ay = np.concatenate((np.linspace(0, 100, 100),
                             np.linspace(100, 0, 100)))
        
        # Super sampled AND with a different heating rate
        bx = np.linspace(0, 20, 2000)
        # Temperature raises and goes down (2 ramps)
        by = np.concatenate((np.linspace(0, 100, 1000),
                             np.linspace(100, 0, 1000)))
        
        out = self.do(ax, ay, bx, by, 'A-B', err=18, tolerance=-1)
        
        #import pylab as pl
        #pl.plot(ax, ay, 'red')
        #pl.plot(bx, by, 'blue')
        #pl.plot(ax, out, 'green')
        #pl.show()
        #self.assertAlmostEqual(ay[-1]-out[-1], 50)        
        

if __name__ == "__main__":
    unittest.main(verbosity=2)
