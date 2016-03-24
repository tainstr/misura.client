#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests DataDecoder"""
import unittest
from nose.plugins.skip import SkipTest

import os
from misura.client.tests import iutils_testing
from misura.client import filedata

temp_file = os.path.join(iutils_testing.data_dir, 'delete_me')

@SkipTest #there's a problem in travis when you try to write files in a test...
class DataDecoder(unittest.TestCase):

    def tearDown(self):
        iutils_testing.silent_remove(temp_file)

    def test(self):
        nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')
        fp = filedata.getFileProxy(nativem4)

        decoder = filedata.DataDecoder()
        decoder.reset(fp, '/hsm/sample0/profile')

        self.assertEqual(decoder.ext, 'Profile')

        r = decoder.get_data(0)
        self.assertIn('0', decoder.cached_profiles)

        self.assertFalse(os.path.exists(temp_file))
        r[1].save(temp_file, 'JPG')
        self.assertTrue(os.path.exists(temp_file))

        r = decoder.get_data(1)
        self.assertIn('1', decoder.cached_profiles)

        r = decoder.get_data(2)
        self.assertIn('2', decoder.cached_profiles)

        fp.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
