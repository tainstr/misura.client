#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Camera ViewerPicture, Human Interactive Test"""
import unittest
import functools
from misura import utils_testing as ut

from misura.client.beholder import picture
from misura.beholder import sim_camera

from misura.microscope import Hsm
from PyQt4 import QtGui
app=False
print 'Importing',__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])
	ut.parallel(True)

def tearDownModule():
	print 'tearDownModule',__name__
	global app
	print 'Quitting app'
	app.quit()
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
		app.exec_()
		
		
		
		
if __name__ == "__main__":
	unittest.main()  
	
