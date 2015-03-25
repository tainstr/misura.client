#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import functools

from misura import utils_testing as ut
from misura.client.acquisition import controls
from misura import instrument
from PyQt4 import QtGui

app=False

print 'Importing',__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	print 'Quitting app'
	app.quit()
	print 'tearDownModule',__name__
	
class Parent(QtGui.QWidget):
	ok=False
	ins=False
	measureDock=False
	snapshotsDock=False
	graphWin=False
	tableWin=False
	logDock=False
	def newTest(self): self.ok=True
	def setInstrument(self,ins): self.ins=ins

#@unittest.skip('')
class Controls(unittest.TestCase):
	def setUp(self):
		self.server=ut.dummyServer()
		self.rem=instrument.Instrument(self.server)
		self.rem.start_acquisition=functools.partial(self.server.set,'isRunning',True)
		self.rem.parent=lambda: self.server
		self.parent=Parent()
		self.ctrl=controls.Controls(self.rem,self.parent)
		self.ctrl.mute=True
		
	def tearDown(self):
		self.rem.stop_acquisition(False)
		
	def check_act(self):
		self.assertEqual(self.ctrl.startAct.isEnabled(),not self.server['isRunning'])
		self.assertEqual(self.ctrl.stopAct.isEnabled(),self.server['isRunning'])
	
#	@unittest.skip('')
	def test_init(self):
		self.check_act()
		
	def test_start(self):
		self.ctrl.start()
		self.assertTrue(self.server['isRunning'])
		self.check_act()
		
	def test_stop(self):
		self.test_start()
		self.ctrl.stop()
		self.assertFalse(self.server['isRunning'])
		self.check_act()
		

@unittest.skipIf(__name__!='__main__','Non interactive.')
class HuControl(unittest.TestCase):	
	def test_hu(self):
		ut.parallel(1)
		self.server=ut.dummyServer()
		self.rem=instrument.Instrument(self.server)
# 		self.rem.start_acquisition=functools.partial(self.server.set,'isRunning',True)
		self.rem.parent=lambda: self.server
		self.parent=Parent()
		self.ctrl=controls.Controls(self.rem,self.parent)
# 		self.ctrl.mute=True
		mw=QtGui.QMainWindow()
		mw.addToolBar(self.ctrl)
		mw.show()
		app.exec_()
		ut.parallel(0)
		
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
