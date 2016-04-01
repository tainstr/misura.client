#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest

import os

from misura.client.tests import iutils_testing

from misura.client.acquisition import measureinfo

from misura.client import filedata



from PyQt4 import QtGui, QtCore

@unittest.skip("Needs the server, so it should not be run automatically")
class MeasureInfo(unittest.TestCase):

    def setUp(self):
        from misura import instrument
        from misura import kiln, flex

        file_proxy = filedata.getFileProxy(
            os.path.join(iutils_testing.data_dir, 'test_video.h5'))
        file_proxy.load_conf()

        proxy = file_proxy.conf

        self.measure_info = measureinfo.MeasureInfo(proxy.hsm)

    def check_tabs(self, number_of_samples):
        self.assertEqual(self.measure_info.count(), 4 + number_of_samples)

    def test_tabs_for_two_samples(self):
        self.measure_info.nobj.current = 2
        self.measure_info.refreshSamples()
        self.check_tabs(2)

        self.measure_info.nobj.current = 1
        self.measure_info.refreshSamples()
        self.check_tabs(1)


if __name__ == "__main__":
    unittest.main()
