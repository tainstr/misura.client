#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the datasets.py module."""
import unittest
import sys
import logging
import os,shutil
from misura.client import filedata
from misura.client.tests import iutils_testing as iut
from PyQt4 import QtGui
import veusz.document as document

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
nativem4=os.path.join(iut.data_dir,'post_m3.h5')
nativem4='/opt/local_data/vertical/VerticalDilatometer_3.h5'

m3names=['t', 'kiln_T', 'smp0_Sint', 'smp0_Ang', 'smp0_Ratio', 'smp0_Area','kiln_S', 'kiln_P', 'smp0_Width']

m4names=['t', 'kiln_slope', 'kiln_C', 'kiln_D', 'kiln_rate', 'kiln_kD', 'kiln_kI', 'kiln_Ts', 'kiln_P',
 'kiln_S', 'kiln_kP', 'kiln_T', 'kiln_var', 'kiln_Te', 'kiln_Tk', 'smp0_ymass', 'smp0_cohe', 'smp0_radius', 'smp0_Sur', 'smp0_circleErr', 
 'smp0_spher', 'smp0_angle', 'smp0_err', 'smp0_iA', 'smp0_iC', 'smp0_iB', 'smp0_iD', 
 'smp0_A', 'smp0_circlePart', 'smp0_angB', 'smp0_angC', 'smp0_angL', 
 'smp0_P', 'smp0_angR', 'smp0_xmass', 'smp0_hsym', 'smp0_e', 'smp0_Vol', 'smp0_h', 
 'smp0_rgn', 'smp0_w', 'smp0_vsym', 'smp0_rdn']


class Doc(object):
	def __init__(self):
		self.data={}
	
class Ds(object):
	def __init__(self,name='ciao'):
		self.n=name
	def name(self):
		return self.n

class TestDatasetPluginEntry(unittest.TestCase):
	"""Tests the operation of importing a misura file, either native or exported from misura3."""	
	def check(self,root,maxst=-1):
		if len(root.children)==0:
			return 
		for c in root.children.values():
			if c.status>maxst:
				maxst=c.status
			# Recursively check
			self.check(c,c.status)
		logging.debug('%s %s %s', 'check', root, maxst)
		self.assertTrue(root.status,maxst)
	
	def _test_dpe(self):
		dpar=Ds('parent')
		dsub=Ds('sub')
		doc=Doc()
		doc.data[dpar.n]=dpar
		doc.data[dsub.n]=dsub
		fold=filedata.NodeEntry(doc,'folder')
		par=filedata.DatasetEntry(doc,path='parent',parent=fold)
		sub=filedata.DatasetEntry(doc,path='sub',parent=par)
		self.assertEqual(len(fold),1)
		self.assertEqual(len(par),1)
		self.assertEqual(len(sub),0)
		self.check(fold)
		sub.status=3
		self.check(fold,3)
		
	def test_import(self):
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc=document.Document()
		imp.do(doc)
		logging.debug('%s', imp.outnames)
		logging.debug('%s', doc.data.keys())
		root=filedata.NodeEntry()
		root.set_doc(doc)
		
		
		
		
if __name__ == "__main__":
	unittest.main()  
