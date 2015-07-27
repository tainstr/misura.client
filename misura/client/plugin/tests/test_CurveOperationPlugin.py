#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing plugin/CurveOperationPlugin.py plugin."""
import unittest
from misura.canon.logger import Log as logging

from misura.client.tests import iutils_testing as iut
from misura.client.plugin import CurveOperationPlugin
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

#@unittest.skip('')


class TestCurveOperationPlugin(unittest.TestCase):

    """Tests the CurveOperationPlugin."""

    def do(self, ax, ay, bx, by, op='A-B', **kw):
        logging.debug('%s', 'creating doc')
        doc = document.Document()
        logging.debug('%s', 'inserting data')
        insertData(doc, {'ax': ax, 'ay': ay, 'bx': bx, 'by': by})
        fields = {'ax': 'ax', 'ay': 'ay', 'bx': 'bx', 'by': 'by', 'ds_out': 'out',
                  'operation': op, 'smooth': False, 'relative': True, 'tolerance': 1.}
        fields.update(kw)
        logging.debug('%s', 'build op')
        p = CurveOperationPlugin(**fields)
        logging.debug('%s', 'get ds')
        p.getDatasets(fields)
        logging.debug('%s', 'update ds')
        out = p.updateDatasets(fields, veusz.plugins.DatasetPluginHelper(doc))
        return out

#	@unittest.skip('')
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
        logging.debug('%s %s', 'Supersampling', sup.sum())
        # Output value should have same length of ref. array, A
        self.assertEqual(len(sup), len(ay))

        # UNDERSAMPLING
        und = self.do(bx, by, ax, ay, 'A-B')
        logging.debug('%s %s', 'Undersampling', und.sum())
        # Output value should have same length of ref. array, B
        self.assertEqual(len(und), len(by))
        self.assertAlmostEqual(sup.sum(), 0)
        self.assertAlmostEqual(und.sum(), 0)

#	@unittest.skip('')
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

# 	@unittest.skip('')
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
        out = self.do(ax, ay, bx, by, 'A-B')
        self.assertAlmostEqual(out.sum() / len(ax), 0, delta=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
