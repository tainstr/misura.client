#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests role selector widget."""
import unittest
from misura.canon.logger import Log as logging
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui,QtCore

logging.debug('%s %s', 'Importing', __name__)
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)

def tearDownModule():
	logging.debug('%s', 'Quitting app')
	logging.debug('%s %s', 'tearDownModule', __name__)


ev=QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPoint(0, 0), QtCore.QPoint(0, 0), 
                     QtCore.Qt.NoButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier)

class FocusableSlider(unittest.TestCase):
	def setUp(self):
		self.wg=widgets.FocusableSlider()
		
	def tearDown(self):
		print 'teardown'
		self.wg.close()
		
	def test_set_paused(self):
		self.assertFalse(self.wg.paused)
		self.assertTrue(self.wg.set_paused(True))
		self.assertTrue(self.wg.paused)
		self.assertTrue(self.wg.set_paused(False))
		self.assertFalse(self.wg.paused)
		self.assertFalse(self.wg.set_paused(False))
		
	def test_mousePressEvent(self):
		print 'a'
		self.assertFalse(self.wg.paused)
		print '0'
		self.wg.mousePressEvent(ev)
		print '1'
		self.assertTrue(self.wg.paused)
		self.wg.mouseReleaseEvent(ev)
		print '2'
		self.assertFalse(self.wg.paused)
		print '3'
		
	def test_mouseDoubleClickEvent(self):
		print 'mdce 1'
		self.assertFalse(self.wg.zoomed)
		self.wg.mouseDoubleClickEvent(ev)
		print 'mdce 2'
		self.assertTrue(self.wg.zoomed)
		self.wg.mouseDoubleClickEvent(ev)
		print 'mdce 3'
		self.assertFalse(self.wg.zoomed)
		print 'done'
	
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
		logging.debug('%s %s %s %s %s %s', 'Current:', w.current, 'Maximim:', w.max, 'Mimimum', w.min)

	def test_float(self):
		self.root.sete('Test', option.ao({}, 'Test', 'Float')['Test'])
		w=self.wgGen()
		self.assertEqual(w.current, 0)
		self.assertFalse(w.slider)
		logging.debug('%s %s %s %s %s %s', 'Current:', w.current, 'Maximim:', w.max, 'Mimimum', w.min)

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
	
	
