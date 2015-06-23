#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.log module."""
import unittest
import os
from misura.client.tests import iutils_testing
from misura.client import fileui
from misura.canon import indexer
from PyQt4 import QtGui




class OfflineLog(unittest.TestCase):
	"""Tests the operation of importing a misura file."""	
	@unittest.skip('not implemented yet')
	def test_log(self):
		fpath = os.path.join(iutils_testing.data_dir, 'test_video.h5')

		fp = indexer.Sh	edFile(fpath)
		log = fileui.OfflineLog(fp)
		txt = log.toPlainText()

		self.assertTrue(txt.startswith('Importing from'), msg = 'Wrong log: ' + txt)

	def test_log_is_not_implemented(self):
		fpath = os.path.join(iutils_testing.data_dir, 'test_video.h5')

		fp = indexer.SharedFile(fpath)
		log = fileui.OfflineLog(fp)

		self.assertEqual('unimplemented', log.toPlainText())
		
if __name__ == "__main__":
	unittest.main()  
