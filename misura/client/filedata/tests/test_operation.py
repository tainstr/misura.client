#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the datasets.py module."""
import unittest
import sys
import os
import shutil
import numpy as np
from misura.client import filedata
from misura.client.tests import iutils_testing
from PyQt4 import QtGui

import veusz.document as document
import veusz.widgets


nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')
nativem4b = os.path.join(iutils_testing.data_dir, 'test_video.h5')

# TODO: derive them from Analyzer definitions!
# 'hsm/sample0/anerr', 'hsm/anerr'

m4names = ['0:hsm/sample0/e', '0:hsm/sample0/h',
           '0:hsm/sample0/circlePart', '0:hsm/sample0/w', '0:hsm/sample0/radius',
           '0:hsm/sample0/iC', '0:hsm/sample0/iB', '0:hsm/sample0/iA', '0:hsm/sample0/iD',
           '0:hsm/sample0/A', '0:hsm/sample0/pot', '0:hsm/sample0/cohe',
           '0:hsm/sample0/P', '0:hsm/sample0/spher', '0:hsm/sample0/hsym', '0:hsm/sample0/rgn',
           '0:hsm/sample0/adh', '0:hsm/sample0/circleErr', '0:hsm/sample0/angle', '0:hsm/sample0/xmass',
           '0:hsm/sample0/angR', '0:hsm/sample0/ymass', '0:hsm/sample0/angL',
           '0:hsm/sample0/angB', '0:hsm/sample0/angC', '0:hsm/sample0/vsym', '0:hsm/sample0/rdn',
           '0:hsm/sample0/Vol', '0:hsm/sample0/Sur', '0:t']


class TestOperationMisuraImport(unittest.TestCase):

    """Tests the operation of importing a misura file, either native or exported from misura3."""

    def check_doc(self, doc, path):
        """Check imported document for standard errors"""
        for k in doc.data.keys():
            ds = doc.data[k]
            ref = 'sample' not in k
            self.assertEqual(
                ds.m_smp.ref, ref, msg='Dataset %s should have reference=%s' % (k, ref))
            self.assertEqual(ds.linked.filename, path)

    def test_1_importFromM4(self):
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=nativem4))
        doc = filedata.MisuraDocument()
        imp.do(doc)
        # autoload
        self.assertGreater(len(doc.data['0:hsm/sample0/h']), 10)
        # no load: ds present but empty
        self.assertIn('0:hsm/sample0/e', doc.available_data)
        self.assertNotIn('0:hsm/sample0/e', doc.data)
        self.assertSetEqual(
            set(m4names) - set(imp.outnames) - set(doc.available_data.keys()), set([]))
        self.check_doc(doc, nativem4)
        # Test single dataset name import
        imp = filedata.OperationMisuraImport.from_dataset_in_file(
            '0:hsm/sample0/e', nativem4)
        imp.do(doc)
        self.assertIn('0:hsm/sample0/e', doc.data)
        self.assertNotIn('0:hsm/sample0/e', doc.available_data)

    def test_2_multiImport(self):
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=nativem4))
        doc = filedata.MisuraDocument()
        imp.do(doc)
        # autoload
        self.assertGreater(len(doc.data['0:hsm/sample0/h']), 10)
        # no load: ds present but empty
        self.assertIn('0:hsm/sample0/e', doc.available_data)
        self.assertNotIn('0:hsm/sample0/e', doc.data)
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=nativem4b))
        imp.do(doc)
        self.assertIn('0:t', imp.outnames)
        self.assertIn('0:t', doc.data.keys())
# 		self.assertSetEqual(set(m4names)-set(imp.outnames),set([]))
# 		self.check_doc(doc,nativem4)

    @unittest.skip('Misura 3 files needed')
    def test_0_importFromM3(self):
        """Test the operation from a Misura3 file"""
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=from3))
        doc = filedata.MisuraDocument()
        imp.do(doc)
        m3names = ['t', 'kiln_T', 'smp0_Sint', 'smp0_Ang',
                   'smp0_Ratio', 'smp0_Area', 'kiln_S', 'kiln_P', 'smp0_Width']
        self.assertEqual(imp.outnames, m3names)
        self.check_doc(doc, from3)

    def tesmmit(self):
        path = 'tmp.h5'
        shutil.copy(from3, 'tmp.h5')
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=path))
        doc = filedata.MisuraDocument()
        imp.do(doc)
        doc.data['smp0_Sint'].linked.commit('test')



class FakeProxy():
    def __init__(self, data):
        self.data = data

    def col(self, col, n):
        return self.data

class TestNotInterpolated(unittest.TestCase):
    def test_not_interpolated_no_adding(self):
        initial_data = np.array([[0., 123.], [1., 321.]])

        actual_output = filedata.operation.not_interpolated(FakeProxy(initial_data), 0, 0, 1)

        np.testing.assert_array_equal(initial_data.transpose(), actual_output)

    def test_not_interpolated_adding_something_in_the_end(self):
        initial_data = np.array([[0., 123.], [1., 321.]])

        actual_output = filedata.operation.not_interpolated(FakeProxy(initial_data), 0, 0, 4)

        expected_output = np.array([[0., 123.], [1., 321.], [2., 321.], [3.5, 321.], [5., 321.]]).transpose()
        np.testing.assert_array_equal(expected_output, actual_output)

    def test_not_interpolated_starting_after_zero(self):
        initial_data = np.array([[0., 123.], [1., 321.], [2., 456.]])

        actual_output = filedata.operation.not_interpolated(FakeProxy(initial_data), 0, 2, 5)

        expected_output = np.array([[0., 123.], [1., 321.], [2., 456.], [3., 456.], [4.5, 456.], [6., 456.]]).transpose()
        np.testing.assert_array_equal(expected_output, actual_output)


if __name__ == "__main__":
    unittest.main()
