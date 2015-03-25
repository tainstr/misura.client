#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests role selector widget."""
import unittest
import functools
from misura import utils_testing as ut
from misura.client import widgets
from misura.canon import option
from misura import kiln, microscope
from PyQt4 import QtGui,QtCore
from PyQt4.QtTest import QTest
app=False
print 'Importing',__name__
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])
	ut.parallel(0)

def tearDownModule():
	global app
	print 'Quitting app'
	app.quit()
	print 'tearDownModule',__name__
	
	
class Role(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.root=ut.dummyServer(kiln.Kiln, microscope.Hsm)
		ut.thermoregulationInit(cls.root)
	
	def test(self):
		w=widgets.build(self.root, self.root.hsm, self.root.hsm.gete('smp0'))
		# The current value is not initialized (gete() returns {current:None} )
		self.assertEqual(w.current, None)
		self.assertEqual(w.button.text(), 'None')
		w.get()
		self.assertEqual(w.current, ['/hsm/sample0/', 'default'])
		e=widgets.RoleEditor(w)
		self.assertEqual(e.tree.current_fullpath(), '/hsm/sample0/')
		self.assertEqual(e.config.itemData(e.config.currentIndex()), 'default')
		self.assertFalse(hasattr(e, 'io'))
		
	def test_io(self):
		w=widgets.build(self.root, self.root.kiln, self.root.kiln.gete('tcs'))
		self.assertEqual(w.current, None)
		self.assertEqual(w.button.text(), 'None')
		w.get()
		self.assertEqual(w.current, ['/kiln/heatload/', 'default', 'temp'])
		e=widgets.RoleEditor(w)
		self.assertEqual(e.tree.current_fullpath(), '/kiln/heatload/')
		ci=e.config.currentIndex()
		self.assertEqual(e.config.itemData(ci), 'default')
		ei=e.io.currentIndex()
		self.assertEqual(e.io.itemData(ei), 'temp')
		e.io.setCurrentIndex(ei-1)
		nval=e.io.itemData(e.io.currentIndex())
		e.apply()
		self.assertEqual(w.current[-1], nval)
		if main:
			w.show()
			QtGui.qApp.exec_()
			print 'Selected on exit:', w.current
		
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
	
