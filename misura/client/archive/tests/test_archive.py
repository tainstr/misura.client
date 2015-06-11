#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import logging
import unittest

import os
from misura.client.tests import iutils_testing as iut
from misura.client import archive, filedata, conf
from misura.client.clientconf import confdb
from PyQt4 import QtGui
app=False

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	app.quit()
	logging.debug('%s %s', 'tearDownModule', __name__)

nativem4=os.path.join(iut.data_dir,'hsm_test.h5')
#@unittest.skip('')
class MainWindow(unittest.TestCase):
	"""Tests the MainWindow"""	
#	@unittest.skip('')
	def test_openfile(self):
		w=archive.MainWindow()
		w.open_file(nativem4)
# 		self.assertEqual(confdb.recent_file[-1][0],nativem4)
		if __name__=='__main__':
			w.show()
			iut.QtGui.qApp.exec_()
		w.close()
		
		
@unittest.skip('')
class TestWindow(unittest.TestCase):
	"""Tests the TestWindow"""	
#	@unittest.skip('')
	def test_openfile(self):
		doc=filedata.MisuraDocument(nativem4)
		w=archive.TestWindow(doc)
		w.close()
		#TODO: check double import of data
		
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
