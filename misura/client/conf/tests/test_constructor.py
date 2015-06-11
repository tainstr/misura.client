#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the programmatic widget construction."""
import unittest
import os
import logging
from misura.client.conf import constructor
from misura.client import filedata
from misura.client.misura3 import convert
from misura.client.tests import iutils_testing as iut
from misura.canon import option
from PyQt4 import QtGui,QtCore

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
	


main=__name__=="__main__"

from3=os.path.join(iut.data_dir,'m3_hsm.h5')
nativem4=os.path.join(iut.data_dir,'hsm_test.h5')

#@unittest.skip('')
class TestOrgSections(unittest.TestCase):
	"""Tests categorizing options."""	
				
		
#	@unittest.skip('')
	def test_orgSections(self):
		"""Tests the distribution of scripts"""
		fp=filedata.getFileProxy(nativem4)
		fp.close()
		sec=constructor.orgSections(fp.conf.post.measure.describe())
		handles=[o['handle'] for o in sec['Main']]
		
		logging.debug('%s %s', '\n'.join(['%s -> %r' % (o['handle'], [c['handle'] for c in o['children']]) for o in sec['Main']]))
		self.assertTrue('param_Sint' not in handles)
		
#@unittest.skip('')		
class TestSection(unittest.TestCase):
	"""Tests the building of a section"""
	
#	@unittest.skip('')
	def test_section(self):
		fp=filedata.getFileProxy(nativem4)
		fp.close()
		std=fp.conf.post.measure
		sec=constructor.orgSections(std.describe())['Main']
		
		obj=constructor.Section(fp.conf,std,sec)
		if main:
			obj.show()
			QtGui.qApp.exec_()	
			
#@unittest.skip('')	
class TestInterface(unittest.TestCase):
	"""Tests the building of a section"""
	
#	@unittest.skip('')
	def test_interface(self):
		fp=filedata.getFileProxy(nativem4)
		fp.close()
		rem=fp.conf.post.measure
		obj=constructor.Interface(fp.conf,rem,rem.describe())
		if main:
			logging.debug('%s', 'Interactive testing')
			obj.show()
			QtGui.qApp.exec_()

	def test_from_convert(self):
		cp=option.ConfigurationProxy(desc=convert.tree_dict.copy())
		cp.iterprint()
		m=cp.hsm.measure
		sec=constructor.orgSections(m.describe())['Main']
		obj=constructor.Section(cp, m, sec)
		if main:
			logging.debug('%s', 'Interactive testing')
			obj.show()
			QtGui.qApp.exec_()			

if main:
	unittest.main()  
