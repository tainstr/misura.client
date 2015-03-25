#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests camera ViewerPicture"""
import unittest
import functools
from misura import utils_testing as ut

from misura.client.beholder import picture
from misura.beholder import sim_camera

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

#@unittest.skip('')
class ViewerPicture(unittest.TestCase):
	def setUp(self):
		self.server=ut.dummyServer()
		self.rem=sim_camera.SimCamera(parent=self.server)
		self.rem.start_acquisition=functools.partial(self.server.set,'isRunning',True)
		self.rem.parent=lambda: self.server
		self.obj=picture.ViewerPicture(self.rem,self.server)
		self.rem.copy=lambda: self.rem
	
	def tearDown(self):
		self.obj.close()
	
	def test_init(self):
		sz=self.rem['size']
		self.assertEqual(self.obj.pix_width,sz[0])
		self.assertEqual(self.obj.pix_height,sz[1])
		self.assertEqual(len(self.obj.samples),1)
		
		
if __name__ == "__main__":
	unittest.main()  
	
