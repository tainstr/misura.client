#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
from misura.canon.logger import Log as logging
import unittest
from misura.client.acquisition import acquisition
from misura import beholder
from misura.canon import option
from misura import server
from PyQt4 import QtGui
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
class MainWindow(unittest.TestCase):
	def setUp(self):
#		self.server=ut.dummyServer(instrument.Instrument)
		self.server=server.MainServer()
		self.server_proxy=option.ConfigurationProxy(self.server.tree()[0])
		self.instr=self.server_proxy.flex
		self.instr=self.server.flex
		self.instr.init_instrument=lambda *foo: True
		self.mw=acquisition.MainWindow()

	def tearDown(self):
		self.mw.close()
		
	def test_setServer(self):
		mw=self.mw
		mw.setServer(self.server)
		n=len(self.server['instruments'])
		self.assertEqual(mw.instrumentSelector.lay.count(),n)
		self.assertEqual(len(mw.myMenuBar.lstInstruments),n)
		self.assertEqual(len(mw.myMenuBar.instruments.actions()),n)
		
	def test_addCamera(self):
		mw=self.mw
		mw.setServer(self.server)
		cam=beholder.SimCamera(self.server)
		mw.addCamera(cam,'camera')
		self.assertEqual(mw.cameras['camera'].remote,cam)
				
	def test_setInstrument(self):
		mw=self.mw
		mw.setServer(self.server_proxy)
		logging.debug('%s %s', 'init_instrument is', self.instr.init_instrument)
		mw.setInstrument(self.instr)
		self.assertEqual(mw.windowTitle(),'misura Acquisition: flex (Optical Fleximeter)')
		self.assertEqual(mw.controls.mute, mw.fixedDoc)
		self.assertEqual(mw.controls.startAct.isEnabled(), not self.server['isRunning'])
		self.assertEqual(mw.controls.stopAct.isEnabled(),self.server['isRunning'])
		self.assertEqual(mw.measureTab.count(),4)
		self.assertEqual(mw.name,'flex')
	

		
if __name__ == "__main__":
	unittest.main()  
