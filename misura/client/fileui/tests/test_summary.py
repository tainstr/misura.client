#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests summary table"""
import unittest
import os
from misura.canon.logger import Log as logging

from misura.client.tests import iutils_testing as iut
from misura.client.fileui import SummaryView
from misura.client import filedata, plugin # neeeded for correct veusz init!

from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)

def tearDownModule():
	logging.debug('%s %s', 'tearDownModule', __name__)

nativem4=os.path.join(iut.data_dir,'hsm_test.h5')
nativem4='/opt/misura/misura/tests/storage/data/hsm/device_12.h5'
		
class TestSummary(unittest.TestCase):
	def setUp(self):
		self.s=SummaryView()
	def test(self):
		doc=filedata.MisuraDocument(nativem4)
		doc.reloadData()
		logging.debug('%s', doc.data.keys())
		self.s.set_doc(doc)
		if __name__=="__main__":
			self.s.show()
			QtGui.qApp.exec_()

if __name__ == "__main__":
	unittest.main(verbosity=2)  
