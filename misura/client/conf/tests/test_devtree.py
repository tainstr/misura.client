#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import os
from misura.client.tests import iutils_testing

from misura import server
from misura.client.conf import devtree
from misura.client import filedata

from PyQt4 import QtGui,QtCore
app=False

nativem4=os.path.join(iutils_testing.data_dir,'measure.h5')


class RecursiveModel(unittest.TestCase):
	def test_recursiveModel(self):
		s=server.BaseServer()
		m=devtree.recursiveModel(s)
		
	def test_fileRecursiveModel(self):
		fp=filedata.getFileProxy(nativem4)
		fp.load_conf()
		m=devtree.recursiveModel(fp.conf)
		fp.close()
		
#TODO: test su fileproxy!

class ServerModel(unittest.TestCase):
	def setUp(self):
		self.s=server.BaseServer()
		self.m=devtree.recursiveModel(self.s)
		
	def test_init(self):
		mod=devtree.ServerModel(self.s)
		
		
if __name__=="__main__":
	unittest.main()  
			
