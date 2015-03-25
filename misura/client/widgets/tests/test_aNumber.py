#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests role selector widget."""
import unittest
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui,QtCore
app=False
print 'Importing',__name__
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	print 'Quitting app'
	app.quit()
	print 'tearDownModule',__name__
	
class aNumber(unittest.TestCase):
	def setUp(self):
		self.root=option.ConfigurationProxy()
		
	def wgGen(self):
		self.assertTrue(self.root.has_key('Test'))
		w=widgets.build(self.root, self.root, self.root.gete('Test'))
		# The current value is not initialized (gete() returns {current:None} )
		self.assertTrue(w is not False)
		return w
		
	def test_integer(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Integer')['Test'])
		w=self.wgGen()
		self.assertEqual(w.current, 0)
		self.assertFalse(w.slider)
		print 'Current:',  w.current,   'Maximim:',  w.max,  'Mimimum',  w.min

	def test_float(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Float')['Test'])
		w=self.wgGen()
		self.assertEqual(w.current, 0)
		self.assertFalse(w.slider)
		print 'Current:',  w.current,   'Maximim:',  w.max,  'Mimimum',  w.min

	def test_MIN_MAX(self):
		self.root.sete('Test', 
		               option.ao({}, 'Test', 'Integer', 5, minimum=-10,  maximum=10)['Test'])
		w=self.wgGen()
		self.assertEqual(w.current, 5)
		self.assertTrue(w.slider)
	
	def test_Properties(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Float', current=120,unit='second')['Test'])
		w=self.wgGen()
		w.lay.addWidget(w.label_widget)
# 		w.spinbox.setReadOnly(True)
		if __name__=='__main__':
			w.show()
			QtGui.qApp.exec_()
			
	def test_units(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Float', units='second')['Test'])
		w=self.wgGen()
		self.assertEqual(w.current, 0)
		self.assertFalse(w.slider)
		#TODO!
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
	
