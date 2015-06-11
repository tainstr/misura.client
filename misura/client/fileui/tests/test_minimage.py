#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.minimage module."""
import unittest
import os
import logging
from misura.client import filedata
from misura.client import fileui
from misura.client.tests import iutils_testing as iut
from misura.canon import indexer
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

class MiniImage(unittest.TestCase):	
	def test_init(self):
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=fpath))
		doc=filedata.MisuraDocument()
		imp.do(doc)
		fp=indexer.SharedFile(fpath)
		decoder=filedata.DataDecoder()
		p='/cam/last_frame'
		decoder.reset(fp,p)
		decoder.start()
		doc.decoders[p]=decoder
		# Create the minimage
		mini=fileui.MiniImage(doc,'/cam/last_frame')
		mini.saveDir='/tmp/'
		mini.set_idx(0)
		mini.save_frame()
		
		
if __name__ == "__main__":
	unittest.main()  
