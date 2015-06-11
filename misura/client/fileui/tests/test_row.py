#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.row module."""
import unittest
import os
import logging
from misura.client import filedata
from misura.client import fileui
from misura.client.tests import iutils_testing as iut
from veusz import widgets # needed for document creation!
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


fpath=os.path.join(iut.data_dir,'hsm_test.h5')

class RowView(unittest.TestCase):	
	def test_set_doc(self):
		rv=fileui.RowView()
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=fpath))
		doc=filedata.MisuraDocument()
		imp.do(doc)
		
		rv.set_doc(doc)
		rv.set_idx(1)
		#FIXME: fix these functions!
		logging.debug('%s %s', 'devmenu', rv.devmenu)
		logging.debug('%s %s', 'header', rv.model().header)
		logging.debug('%s %s', 'tree', rv.model().tree)
		
		
if __name__ == "__main__":
	unittest.main()  
