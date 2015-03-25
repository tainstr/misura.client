#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.log module."""
import unittest
import os
from misura.client.tests import iutils_testing as iut
from misura.client import fileui
from misura.canon import indexer
from PyQt4 import QtGui
app=False

print 'Importing',__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	app.quit()
	print 'tearDownModule',__name__


fpath=os.path.join(iut.data_dir,'m3_hsm.h5')


class OfflineLog(unittest.TestCase):
	"""Tests the operation of importing a misura file, either native or exported from misura3."""	
	def test_log(self):
		fp=indexer.SharedFile(fpath)
		log=fileui.OfflineLog(fp)
		txt=log.toPlainText()
		self.assertTrue(txt.startswith('Importing from'),msg='Wrong log: '+txt)
		
		
		
if __name__ == "__main__":
	unittest.main()  
