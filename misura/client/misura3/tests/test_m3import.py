#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Verify conversion from Misura3 to misura files. Windows-only unittest!"""
import sip
sip.setapi('QString', 2)
import unittest
import sys
import pickle

import tables
from tables.nodes import filenode
import veusz.document as document

from misura.client import archive
from misura.client.misura3 import convert
from misura.client.conf import devtree
from misura.canon import reference
from misura.canon import indexer

from misura.client import filedata
from PyQt4 import QtGui

from misura.client.tests import iutils_testing as iut

app=False
def setUpModule():
	global app
	if sys.platform not in ['win32','win64']:
		raise unittest.SkipTest( 'Misura3->misura conversion is available only in windows platforms.')
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	if app: app.quit()
	del app
	
	
hsm_names=set(['t','/hsm/sample0/Ang','/hsm/sample0/Area','/hsm/sample0/Sint','/hsm/sample0/Ratio',
		'/kiln/P','/kiln/T','/kiln/S']) #,'/hsm/sample0/Width','/hsm/sample0/Softening'
hsmDoble_names=set(['t','/kiln/T','/hsm/sample0/Sint','/hsm/sample0/Ang','/hsm/sample0/Ratio',
			'/hsm/sample0/Area']) #,'/hsm/sample0/Width','/hsm/sample0/Softening'
dil_names=set(['t','/kiln/T','/horizontal/sample0/Dil','/kiln/S','/horizontal/sample0/camA',
			'/horizontal/sample0/camB','/kiln/P','/horizontal/sample0/Mov'])
flex_names=set(['t','/kiln/T','/flex/sample0/Flex','/kiln/S','/flex/sample0/camA','/kiln/P','/flex/sample0/Mov'])
class Convert(unittest.TestCase):
	"""Verify conversion from Misura3 to misura files. Windows-only!"""
		
	def check_logging(self,op):
		"""Check length and content of log reference"""
		t=tables.openFile(op,mode='r')
		log=t.root.log[:]
		t.close()
		self.assertEqual(len(log),5)
		# Decode first log line
		msg=reference.Binary.decode(log[0])
		self.assertEqual(msg[0],0)
		self.assertTrue(msg[1].startswith('Importing from'))
		
	
	def check_images(self,op,fmt='m3'):
		"""Check imported images"""
		dec=filedata.DataDecoder()
		fp=indexer.SharedFile(op)
		dec.reset(proxy=fp,datapath='/beholder/idx0/last_frame',ext='img')
		t,img=dec.get_data(0)
		self.assertEqual(img.width(),640)
		self.assertEqual(img.height(),480)
		ofmt=fp.get_node_attr('/beholder/idx0/last_frame','format')
		
		N=len(fp.test.uid('uid').test.root.beholder.idx0.last_frame)
		t,last_img=dec.get_data(N-1)
		
		dec.close()
		fp.close()	# dec uses a copy of fp: must close both!
		
		self.assertTrue(img)
		self.assertEqual(fmt,ofmt)
		self.assertTrue(last_img)
	
	def check_import(self,op,names=False):
		"""Simulate a data import operation"""
		print 'check_import',op
		fp=indexer.SharedFile(op)
		rm=devtree.recursiveModel(fp.conf)
		fp.close()
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=op))
		doc=document.Document()
		imp.do(doc)
		# Build dataset tree
		tree=filedata.get_datasets_tree(doc)
		if names is not False:
			self.assertEqual(set(imp.outdatasets),names)
		return doc
	
	def check_standard(self,op):
		"""Perform a re-standard"""
		#TODO: create test files with Width variable!
		fp=indexer.SharedFile(op)
		fp.conf.hsm.distribute_scripts()
		hdf=fp.test.uid(fp.uid)
		fp.conf.hsm.characterization(hdf.test)
		fp.close()
		
	
#	@unittest.skip('')
	def test_0_data(self):
		"""Conversion of data and configuration"""
		op=convert.convert(iut.db3_path, '00001S',force=True,keep_img=True)
		self.assertTrue(op,'Conversion Failed')
		t=tables.openFile(op,mode='r')
		n=filenode.openNode(t.root.conf)
		tree=pickle.loads(n.read())
		measure=tree['hsm']['measure']['self']
		self.assertEqual(measure['nSamples']['current'],1)
		sumT=t.root.kiln.T
		nrows=len(sumT)
		inidim=getattr(t.root.hsm.sample0.Sint.attrs,'initialDimension',None)
		t0=sumT[0][0]
		T0=sumT[0][1]
		h0=t.root.hsm.sample0.Sint[0][1]
		log=t.root.log[:]
		t.close()
		self.check_standard(op)
		self.check_logging(op)
		self.check_import(op,hsm_names)
		self.check_images(op)
		self.assertEqual(nrows,158)
		self.assertEqual(t0,0.0)
		self.assertEqual(T0,361.0)
		self.assertEqual(h0,100.0)
		self.assertEqual(inidim,3000)

	
	@unittest.skip('')
	def test_1_formats(self):
		# Test jpeg format
		op=convert.convert(iut.db3_path, '00001S',force=True,img=True,keep_img=False,format='jpeg')
		self.check_images(op,'jpeg')
		# Test m3 format
		op=convert.convert(iut.db3_path, '00001S',force=True,img=True,keep_img=False,format='m3')
		self.check_images(op,'m3')
		# Test m4 format
		op=convert.convert(iut.db3_path, '00001S',force=True,img=True,keep_img=False,format='m4')
		self.check_images(op,'m4')

		
	@unittest.skip('')
	def test_2_noforce(self):
		op=convert.convert(iut.db3_path, '00001S',force=False,img=True)
		self.assertTrue(op)
		
	@unittest.skip('')
	def test_3_keepimg(self):
		op=convert.convert(iut.db3_path, '00001S',force=True,img=True,keep_img=True)
		self.assertTrue(op)	
		
		
	@unittest.skip('')
	def test_8_importConverted(self):
		# Convert just data and conf
		op=convert.convert(iut.db3_path, '00001S',force=True,keep_img=True)
		self.assertTrue(op)
		doc=self.check_import(op,hsm_names)
		self.assertEqual(doc.data['/hsm/sample0/Sint'].m_initialDimension,3000.)
		self.assertEqual(doc.data['/hsm/sample0/Sint'].m_percent,True)
#		self.assertEqual(doc.data['/hsm/sample0/Width'].m_initialDimension,2000.)
#		self.assertEqual(doc.data['/hsm/sample0/Width'].m_percent,False)
		
	@unittest.skip('')
	def test_8a_importConvertedDil(self):
		# Dilatometer test
		op=convert.convert(iut.db3_path, '00005H',force=True)
		self.assertTrue(op)
		doc=self.check_import(op,dil_names)
		self.assertEqual(doc.data['/horizontal/sample0/Dil'].m_initialDimension,51000.)
		self.assertEqual(doc.data['/horizontal/sample0/Dil'].m_percent,True)
		self.assertEqual(doc.data['/horizontal/sample0/camA'].m_initialDimension,51000.)
		self.assertEqual(doc.data['/horizontal/sample0/camA'].m_percent,False)
		self.assertEqual(doc.data['/horizontal/sample0/camB'].m_initialDimension,51000.)
		self.assertEqual(doc.data['/horizontal/sample0/camB'].m_percent,False)
		
	@unittest.skip('')
	def test_8b_importConvertedFlex(self):
		# Dilatometer test
		op=convert.convert(iut.db3_path, '00006F',force=True)
		self.assertTrue(op)
		doc=self.check_import(op,flex_names)
		self.assertEqual(doc.data['/flex/sample0/Flex'].m_initialDimension,70000.)
		self.assertEqual(doc.data['/flex/sample0/Flex'].m_percent,True)
		self.assertEqual(doc.data['/flex/sample0/camA'].m_initialDimension,70000.)
		self.assertEqual(doc.data['/flex/sample0/camA'].m_percent,False)
		
	@unittest.skip('')
	def test_9_toArchive(self):
		op=convert.convert(iut.db3_path, '00001S',force=True,keep_img=True)
		# problema widgetregistry
		mw=archive.MainWindow()
		mw.open_file(op)
		
	@unittest.skip('')
	def test_double_samples(self):
		op=convert.convert(iut.db3_path, '00008L',force=True,keep_img=True)
		self.assertTrue(op,'Conversion Failed')
		self.check_images(op, 'm3')
		self.check_import(op,hsmDoble_names)
		op=convert.convert(iut.db3_path, '00008R',force=True,keep_img=True)
		self.assertTrue(op,'Conversion Failed')		
		self.check_images(op, 'm3')
		self.check_import(op,hsmDoble_names)
		
	@unittest.skip('')
	def test_softening(self):
		op=convert.convert(iut.db3_path, '00011S',force=True)
		self.check_import(op,hsm_names)
		op=convert.convert(iut.db3_path, '00010R',force=True)
		self.check_import(op,hsmDoble_names)
		op=convert.convert(iut.db3_path, '00010L',force=True)
		self.check_import(op,hsmDoble_names)
		
if __name__ == "__main__":
	unittest.main()  
