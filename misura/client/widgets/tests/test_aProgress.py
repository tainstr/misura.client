#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests role selector widget."""
import unittest
import functools
from misura.client.tests import iutils_testing
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui,QtCore
from PyQt4.QtTest import QTest

main = __name__=='__main__'

#TODO: generalize a widget testing  framework

class aProgress(unittest.TestCase):
	def setUp(self):
		self.root = option.ConfigurationProxy()
		self.root.sete('name', option.ao({}, 'name', 'String', 'object name')['name'])
		
	def wgGen(self, name):
		self.assertTrue(self.root.has_key(name))

		widget = widgets.build(self.root, self.root, self.root.gete(name))
		self.assertTrue(widget is not False)
		return widget

	def show(self, widget):
		if __name__=='__main__':
			widget.show()
			QtGui.qApp.exec_()
			
		
	def test_zero(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Progress')['Test'])
		widget = self.wgGen('Test')
		self.assertEqual(widget.current, 0)
		self.show(widget)
	
	def test_more(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Progress', current = 3, max = 10)['Test'])
		widget = self.wgGen('Test')
		self.show(widget)
			
	def test_RoleProgress(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Progress', current=3, max = 10)['Test'])
		self.root.sete('Test2', option.ao({}, 'Test2', 'Progress', current=5, max = 8)['Test2'])

		self.root.sete('progress', option.ao({}, 'progress', 'List', current=['/Test', '/Test2'])['progress'])
		self.root.setattr('progress', 'kid', '/progress')

		widget = self.wgGen('progress')
		self.show(widget)
			
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
	

