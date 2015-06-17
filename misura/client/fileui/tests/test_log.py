#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.log module."""
import unittest
import os
from misura.canon.logger import Log as logging
from misura.client.tests import iutils_testing as iut
from misura.client import fileui
from misura.canon import indexer
from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)

def tearDownModule():
	logging.debug('%s %s', 'tearDownModule', __name__)


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
