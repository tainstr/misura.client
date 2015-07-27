#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Verify that versioning of data and metadata works in the test file (conf and summary objects)."""
import unittest
import sys
import os
import veusz.document as document
from misura.client import filedata
import iutils_testing as iut
import shutil
import numpy as np
from PyQt4 import QtGui

from3 = os.path.join(iut.data_dir, 'm3_hsm.h5')
nativem4 = os.path.join(iut.data_dir, 'measure.h5')


class TestSummaryVersioning(unittest.TestCase):

    """Tests the creation, navigation and loading of versions."""

    @classmethod
    def setUpClass(cls):
        cls.path = os.path.join(iut.data_dir, 'versions.h5')
        shutil.copy(nativem4, cls.path)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.path)

    def setUp(self):
        self.file_proxy = filedata.getFileProxy(self.path)

    def tearDown(self):
        self.file_proxy.close()

    def test_0_virgin(self):
        versions = self.file_proxy.get_versions()

        no_version_yet = ''
        actual_version_name = versions[no_version_yet][0]

        self.assertEqual(1, len(versions))
        self.assertEqual("Original", actual_version_name)

    def test_1_save(self):
        self.file_proxy.load_conf()
        original_name = self.file_proxy.conf['name']

        self.file_proxy.conf['name'] = 'pippo'

        self.file_proxy.create_version('any version name')
        self.file_proxy.save_conf(tree=self.file_proxy.conf.tree())

        versions = self.file_proxy.get_versions()

        self.assertEqual(2, len(versions))
        self.assertEqual(versions['/ver_1'][0], 'any version name')

        self.file_proxy.set_version(0)
        self.assertEqual(self.file_proxy.conf['name'], original_name)

        self.file_proxy.set_version(1)
        self.assertEqual(self.file_proxy.conf['name'], 'pippo')


if __name__ == "__main__":
    unittest.main()
