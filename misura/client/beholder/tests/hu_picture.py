#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Camera ViewerPicture, Human Interactive Test"""
from misura.canon.logger import Log as logging
import unittest
import functools
from misura import utils_testing as ut

from misura.client.beholder import picture
from misura.beholder import sim_camera

from misura.microscope import Hsm
from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	ut.parallel(True)

def tearDownModule():
	logging.debug('%s %s', 'tearDownModule', __name__)
	logging.debug('%s', 'Quitting app')
	ut.parallel(False)

class HuViewerPicture(unittest.TestCase):
	def setUp(self):
		self.server=ut.dummyServer(Hsm)
		self.server.hsm.sample0.analyzer.autoroi['Hmargin']=25
		self.server.hsm.sample0.analyzer.autoroi['Vmargin']=25
		self.server.hsm['nSamples']=1
		self.rem=sim_camera.SimCamera(parent=self.server)
		self.rem.encoder['react']='Strictly Follow'
		self.rem['smp0']=[self.server.hsm.sample0['fullpath'],'default']
		self.rem.start_acquisition=functools.partial(self.server.set,'isRunning',True)
		self.rem.parent=lambda: self.server
		self.obj=picture.ViewerPicture(self.rem,self.server)
		self.rem.copy=lambda: self.rem
	
	def tearDown(self):
		self.obj.close()
		
	def test_exec(self):
		self.obj.show()
		QtGui.qApp.exec_()
		
		
		
		
if __name__ == "__main__":
	unittest.main()  
	
