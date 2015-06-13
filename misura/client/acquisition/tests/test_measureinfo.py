#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
from misura.canon.logger import Log as logging
import unittest
import functools

from misura import utils_testing as ut

from misura.client.acquisition import measureinfo
from misura import instrument

from test_controls import Parent
from misura.canon import option
from misura import kiln, flex

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
	
	

#@unittest.skip('')
class MeasureInfo(unittest.TestCase):
	def setUp(self):
		logging.debug('%s', 'setting up')
		self.server=ut.dummyServer(flex.Flex)
		proxy=option.ConfigurationProxy(self.server.tree()[0])
		proxy._parent=option.ConfigurationProxy(self.server.tree()[0])
		logging.debug('%s', proxy.flex)
		logging.debug('%s', proxy.flex.measure)
		logging.debug('%s', proxy.flex.parent)
		self.m=measureinfo.MeasureInfo(proxy.flex)
		
	def check_tabs(self):
		s=self.rem.measure['nSamples']
		self.assertEqual(self.m.count(),3+s)
			
	def test_tabs(self):
		return
		logging.debug('%s', 'test_tabs')
		self.m.remote.measure['nSamples']=2
		self.m.refreshSamples()
		self.check_tabs()
		self.m.remote.measure['nSamples']=1
		self.m.refreshSamples()
		self.check_tabs()
			
		
if __name__ == "__main__":
	unittest.main() 
	
