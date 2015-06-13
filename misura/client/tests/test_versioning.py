#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Verify that versioning of data and metadata works in the test file (conf and summary objects)."""
import unittest
import sys
import os
from misura.canon.logger import Log as logging
import veusz.document as document
from misura.client import filedata
import iutils_testing as iut
import shutil
import numpy as np
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

from3=os.path.join(iut.data_dir,'m3_hsm.h5')
nativem4=os.path.join(iut.data_dir,'hsm_test.h5')


class TestSummaryVersioning(unittest.TestCase):
	"""Tests the creation, navigation and loading of versions of summary table."""	

	@classmethod
	def setUpClass(cls):
		cls.path=os.path.join(iut.data_dir,'versions.h5')
		shutil.copy(nativem4,cls.path)
		
	@classmethod
	def tearDownClass(cls):
		logging.debug('%s', 'teardown')
		os.remove(cls.path)
		
#	@unittest.skip('')
	def test_0_virgin(self):
		"""Check if an unversioned file returns the expected versions."""
		fp=filedata.getFileProxy(self.path)
		cur,avail,info=fp.get_versions('/summary')
		self.assertEqual(cur,-1)
		self.assertEqual(avail,[0])
		self.assertEqual(info,[('Original','')])
		fp.close()
		
	def test_1_save(self):
		"""Check if saving works"""
		fp=filedata.getFileProxy(self.path)
		colnames=fp.header()
		coldatas=[]
		for n in colnames:
			coldatas.append(fp.col(n))
		old=coldatas[0][0]
		new=old+1
		coldatas[0][0]=new
		# Save as version labelled 'Test'
		fp.save_summary(colnames,coldatas,'Test')
		
		# Read back available verisons
		cur,avail,info=fp.get_versions('/summary')
		self.assertEqual(cur,-1)
		self.assertEqual(avail,[0,1])
		self.assertEqual(info[0],('Original',''))
		self.assertEqual(info[1][0],'Test')
		
		# Read new value
		self.assertEqual(fp.col(colnames[0])[0],new)
		
		# Load original version
		fp.set_version('/summary',0)
		self.assertEqual(fp.col(colnames[0])[0],old)
		
		fp.close()	
		
	def test_2_reloading(self):
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=self.path))
		doc=document.Document()
		otm=filedata.DocumentModel(doc)
		otm.pause()
		imp.do(doc)
		otm.pause(False)
		otm.refresh()
#		otm.index(1,0,otm.root)
		# Reload links
		otm.pause()
		LF=doc.data['0:t'].linked
		LF.reloadLinks(doc)
		otm.pause(False)
		otm.refresh()
#		otm.index(1,0,otm.root)
		return doc
			
		
		
if __name__ == "__main__":
    unittest.main()  
