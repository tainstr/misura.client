#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
from misura.client.tests import iutils_testing
import unittest
from misura.client.acquisition import acquisition
from misura import beholder
from misura.canon import option
from misura import server
from PyQt4 import QtGui

class MainWindow(unittest.TestCase):
	def setUp(self):
		self.server=server.MainServer()
		self.server_proxy=option.ConfigurationProxy(self.server.tree()[0])
		self.instr=self.server_proxy.flex
		self.instr=self.server.flex
		self.instr.init_instrument=lambda *foo: True
		self.main_window = acquisition.MainWindow()

	def tearDown(self):
		self.main_window.close()
		
	def test_setServer(self):
		main_window = self.main_window
		main_window.setServer(self.server)
		instruments_count = len(self.server['instruments'])

		self.assertEqual(main_window.instrumentSelector.lay.count(),instruments_count)
		self.assertEqual(len(main_window.myMenuBar.lstInstruments),instruments_count)
		self.assertEqual(len(main_window.myMenuBar.instruments.actions()),instruments_count)
		
	def test_addCamera(self):
		main_window = self.main_window
		main_window.setServer(self.server)
		cam = beholder.SimCamera(self.server)
		main_window.addCamera(cam,'camera')

		self.assertEqual(main_window.cameras['camera'][0].remote, cam)
				
	@unittest.skip("at the moment it's too difficult to mock the MainServer")
	def test_setInstrument(self):
		main_window = self.main_window
		main_window.setServer(self.server_proxy)
		main_window.setInstrument(self.instr)

		self.assertEqual(main_window.windowTitle(),'misura Acquisition: flex (Optical Fleximeter)')
		self.assertEqual(main_window.controls.mute, main_window.fixedDoc)
		self.assertEqual(main_window.controls.startAct.isEnabled(), not self.server['isRunning'])
		self.assertEqual(main_window.controls.stopAct.isEnabled(),self.server['isRunning'])
		self.assertEqual(main_window.measureTab.count(),4)
		self.assertEqual(main_window.name,'flex')
	

		
if __name__ == "__main__":
	unittest.main()  
