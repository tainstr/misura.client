#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the datasets.py module."""
import unittest
import sys
from misura.canon.logger import Log as logging
import os,shutil
from misura.client import filedata
from misura.client.tests import iutils_testing as iut
from PyQt4 import QtGui

import veusz.document as document
import veusz.widgets

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)

def tearDownModule():
	logging.debug('%s %s', 'tearDownModule', __name__)


from3=os.path.join(iut.data_dir,'m3_hsm.h5')
nativem4=os.path.join(iut.data_dir,'hsm_test.h5')
nativem4='/opt/misura/misura/storage/data/hsm/cotto.h5'
nativem4b='/opt/misura/misura/tests/storage/data/flex/dynamic_200_6.h5'

m3names=['t', 'kiln_T', 'smp0_Sint', 'smp0_Ang', 'smp0_Ratio', 'smp0_Area','kiln_S', 'kiln_P', 'smp0_Width']

#TODO: derive them from Analyzer definitions!
# 'hsm/sample0/anerr', 'hsm/anerr'
m4names=[ 'hsm/sample0/e', 'hsm/sample0/h', 
		 'hsm/sample0/circlePart', 'hsm/sample0/w', 'hsm/sample0/radius', 
		'hsm/sample0/iC', 'hsm/sample0/iB', 'hsm/sample0/iA', 'hsm/sample0/iD',  
		'hsm/sample0/A', 'hsm/sample0/pot', 'hsm/sample0/cohe', 
		'hsm/sample0/P', 'hsm/sample0/spher', 'hsm/sample0/hsym', 'hsm/sample0/rgn', 
		'hsm/sample0/adh', 'hsm/sample0/circleErr', 'hsm/sample0/angle', 'hsm/sample0/xmass', 
		'hsm/sample0/angR', 'hsm/sample0/ymass', 'hsm/sample0/angL', 
		'hsm/sample0/angB', 'hsm/sample0/angC', 'hsm/sample0/vsym', 'hsm/sample0/rdn', 
		'hsm/sample0/Vol', 'hsm/sample0/Sur', 't']

class TestOperationMisuraImport(unittest.TestCase):
	"""Tests the operation of importing a misura file, either native or exported from misura3."""	
	
	def check_doc(self,doc,path):
		"""Check imported document for standard errors"""
		for k in doc.data.keys():
			ds=doc.data[k]
			ref='sample' not in k
			self.assertEqual(ds.m_smp.ref,ref,msg='Dataset %s should have reference=%s' % (k,ref))
			self.assertEqual(ds.linked.filename,path)
				
		
# 	@unittest.skip('')
	def test_0_importFromM3(self):
		"""Test the operation from a Misura3 file"""
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=from3))
		doc=document.Document()
		imp.do(doc)
		self.assertEqual(imp.outnames,m3names)
		self.check_doc(doc,from3)
		
#	@unittest.skip('')
	def test_1_importFromM4(self):
		"""Test the operation from a Misura3 file"""
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc=document.Document()
		imp.do(doc)
		logging.debug('%s', imp.outnames)
		logging.debug('%s', doc.data.keys())
		# autoload
		self.assertGreater(len(doc.data['hsm/sample0/h']),10)
		# no load: ds present but empty
		self.assertEqual(len(doc.data['hsm/sample0/e']),0)
		self.assertSetEqual(set(m4names)-set(imp.outnames),set([]))
		self.check_doc(doc,nativem4)
		
#	@unittest.skip('')
	def test_2_multiImport(self):
		"""Test the operation from a Misura3 file"""
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc=document.Document()
		imp.do(doc)
		logging.debug('%s', imp.outnames)
		logging.debug('%s', doc.data.keys())
		# autoload
		self.assertGreater(len(doc.data['hsm/sample0/h']),10)
		# no load: ds present but empty
		self.assertEqual(len(doc.data['hsm/sample0/e']),0)
		
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4b))
		imp.do(doc)
		logging.debug('%s %s', 'second', imp.outnames)
		logging.debug('%s %s', 'second', doc.data.keys())
		self.assertIn('0:t',imp.outnames)
		self.assertIn('t',doc.data.keys())
		self.assertIn('0:t',doc.data.keys())	
# 		self.assertSetEqual(set(m4names)-set(imp.outnames),set([]))
# 		self.check_doc(doc,nativem4)		
		
		
	def tesmmit(self):
		path='tmp.h5'
		shutil.copy(from3,'tmp.h5')
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=path))
		doc=document.Document()
		imp.do(doc)
		doc.data['smp0_Sint'].linked.commit('test')
		
		
if __name__ == "__main__":
	unittest.main()  
