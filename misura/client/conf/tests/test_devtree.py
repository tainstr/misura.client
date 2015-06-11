#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import os
import logging
import functools
from misura import utils_testing as ut
from misura.client.tests import iutils_testing as iut

from misura import server
from misura.client.conf import devtree
from misura.client import filedata

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
	
nativem4=os.path.join(iut.data_dir,'hsm_test.h5')


#@unittest.skip('')
class RecursiveModel(unittest.TestCase):
#	@unittest.skip('')
	def test_recursiveModel(self):
		s=server.BaseServer()
		m=devtree.recursiveModel(s)
		logging.debug('%s', m)
		
	def test_fileRecursiveModel(self):
		fp=filedata.getFileProxy(nativem4)
		fp.load_conf()
		m=devtree.recursiveModel(fp.conf)
		fp.close()
		
#TODO: test su fileproxy!

#@unittest.skip('')		
class ServerModel(unittest.TestCase):
	def setUp(self):
		self.s=server.BaseServer()
		self.m=devtree.recursiveModel(self.s)
		
	def test_init(self):
		mod=devtree.ServerModel(self.s)
		
		
if __name__=="__main__":
	unittest.main()  
			
