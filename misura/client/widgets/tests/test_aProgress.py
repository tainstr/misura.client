#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests role selector widget."""
import unittest
import functools
from misura.canon.logger import Log as logging
from misura import utils_testing as ut
from misura.client import widgets
from misura.device import Node 
from misura.canon import option
from PyQt4 import QtGui,QtCore
from PyQt4.QtTest import QTest
app=False
logging.debug('%s %s', 'Importing', __name__)
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	global app
	app=QtGui.QApplication([])
	ut.parallel(0)

def tearDownModule():
	global app
	logging.debug('%s', 'Quitting app')
	app.quit()
	logging.debug('%s %s', 'tearDownModule', __name__)
	
class aProgress(unittest.TestCase):
	def setUp(self):
		self.root=Node()
		self.root.sete('name', option.ao({}, 'name', 'String', 'object name')['name'])
		
	def wgGen(self, name='Test'):
		self.assertTrue(self.root.has_key(name))
		w=widgets.build(self.root, self.root, self.root.gete(name))
		# The current value is not initialized (gete() returns {current:None} )
		self.assertTrue(w is not False)
		return w
		
	def test_zero(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Progress')['Test'])
		w=self.wgGen()
		self.assertEqual(w.current, 0)
		if __name__=='__main__':
			w.show()
			QtGui.qApp.exec_()
	
	def test_more(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Progress', current=3, maximum=10)['Test'])
		w=self.wgGen()
		if __name__=='__main__':
			w.show()
			QtGui.qApp.exec_()
			
	def test_RoleProgress(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Progress', current=3, maximum=10)['Test'])
		self.root.sete('Test2', option.ao({}, 'Test2', 'Progress', current=5, maximum=8)['Test2'])
		self.root.sete('progress', option.ao({}, 'progress', 'List', current=['/Test', '/Test2'])['progress'])
		w=self.wgGen('progress')
		if __name__=='__main__':
			w.show()
			QtGui.qApp.exec_()
			
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
	
