#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest

import os
from misura.client.tests import iutils_testing
from misura.client import archive, filedata, conf
from misura.client.clientconf import confdb
import shutil

from PyQt4 import QtGui



test_file_name = os.path.join(iutils_testing.data_dir,'archive_test.h5')

@unittest.skip('this causes ICE error...')
class MainWindow(unittest.TestCase):
	def tearDown(self):
		iutils_testing.silent_remove(test_file_name)

	def test_openfile(self):
		shutil.copy(os.path.join(iutils_testing.data_dir,'measure.h5'), test_file_name)

		main_window = archive.MainWindow()
		main_window.open_file(test_file_name)

		iutils_testing.show(main_window, __name__)
		
		main_window.close()
		
		
@unittest.skip('')
class TestWindow(unittest.TestCase):
	def test_openfile(self):
		doc=filedata.MisuraDocument(test_file_name)
		w=archive.TestWindow(doc)
		w.close()
		
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
