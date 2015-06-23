#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests DataDecoder"""
import unittest

import os
from misura.client.tests import iutils_testing 
from misura.client import archive, filedata, conf

from PyQt4 import QtGui

temp_file = os.path.join(iutils_testing.data_dir, 'delete_me')

class DataDecoder(unittest.TestCase):
	def tearDown(self):
		iutils_testing.silent_remove(temp_file)

	def test(self):
		nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')
		fp = filedata.getFileProxy(nativem4)

		decoder = filedata.DataDecoder()
		decoder.reset(fp,'/hsm/sample0/profile')
		
		self.assertEqual(decoder.ext, 'Profile')
		
		self.assertFalse(os.path.exists('%s/0.npy' % decoder.tmpdir))
		r = decoder.get_data(0)
		self.assertTrue(os.path.exists('%s/0.npy' % decoder.tmpdir))

		self.assertFalse(os.path.exists(temp_file))
		r[1].save(temp_file ,'JPG')
		self.assertTrue(os.path.exists(temp_file))

		self.assertFalse(os.path.exists('%s/1.npy' % decoder.tmpdir))
		r = decoder.get_data(1)
		self.assertTrue(os.path.exists('%s/1.npy' % decoder.tmpdir))

		self.assertFalse(os.path.exists('%s/2.npy' % decoder.tmpdir))
		r = decoder.get_data(2)
		self.assertTrue(os.path.exists('%s/2.npy' % decoder.tmpdir))

		fp.close()	

if __name__ == "__main__":
	unittest.main(verbosity=2) 