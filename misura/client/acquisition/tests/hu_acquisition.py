#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import logging
import unittest
from misura.client.acquisition import MainWindow
from misura import utils_testing as ut
from misura.client.tests import iutils_testing as iut
from PyQt4 import QtGui
app=False

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	ut.parallel(1)
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	ut.parallel(0)
	global app
	app.quit()
	logging.debug('%s %s', 'tearDownModule', __name__)

class HuAcquisition(unittest.TestCase):
	def setUp(self):
		self._root=ut.full_hsm()
		self.root=iut.FakeProxy(self._root)

	def tearDown(self):
		self._root.close()
		
# 	@unittest.skip('')
	def test_setInstrument(self):
		self.mw=MainWindow()
		logging.debug('%s %s %s', 'setting instrument', self.root.hsm, self.root)
		self.mw.setInstrument(self.root.hsm,self.root)
		self.mw.show()
		app.exec_()
		
	@unittest.skip('')	
	def test_serve(self):
		p,main=ut.serve(self.root,3880)
		p.start()
		p.join()
		
if __name__ == "__main__":
	unittest.main()  
	
	
