#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests summary table"""
import unittest
import os

from misura.client.tests import iutils_testing as iut
from misura.client.fileui import SummaryView
from misura.client import filedata, plugin # neeeded for correct veusz init!

from PyQt4 import QtGui
app=False

print 'Importing',__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	app.quit()
	print 'tearDownModule',__name__

nativem4=os.path.join(iut.data_dir,'hsm_test.h5')
nativem4='/opt/misura/misura/tests/storage/data/hsm/device_12.h5'
		
class TestSummary(unittest.TestCase):
	def setUp(self):
		self.s=SummaryView()
	def test(self):
		doc=filedata.MisuraDocument(nativem4)
		doc.reloadData()
		print doc.data.keys()
		self.s.set_doc(doc)
		if __name__=="__main__":
			self.s.show()
			app.exec_()

if __name__ == "__main__":
	unittest.main(verbosity=2)  
