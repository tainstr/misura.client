#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import os

from misura import utils_testing as ut
from misura import parameters as params
from misura.canon.indexer import SharedFile
from misura.client import video
from PyQt4 import QtGui

print 'Importing '+__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])
	
def tearDownModule():
	global app
	app.quit()
	print 'tearDownModule',__name__
		

m4file=params.testdir+'storage/hsm_test.h5'	
m4file='/home/daniele/f3x3.h5'
output='/home/daniele/output.avi'
		
class Video(unittest.TestCase):
	
	@unittest.skipIf(__name__!='__main__','Not interactive')
	def test_gui(self):
		sh=SharedFile(m4file)
		v=video.VideoExporter(sh)
		v.show()
		app.exec_()
		sh.close()
		
# 	@unittest.skip('')
	def test_export_image(self):
		sh=SharedFile(m4file)
		video.export(sh,output=output)
		sh.close()
	
	def test_export_profile(self):
		sh=SharedFile(m4file)
		video.export(sh,'/hsm/sample0/profile',output=output)
		sh.close()
		
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
		
