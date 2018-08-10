#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.log module."""
import unittest
import os
from misura.client.tests import iutils_testing
from misura.client import fileui
from misura.client.fileui.log import ReferenceLogModel
from misura.canon import indexer
from PyQt4 import QtGui, QtCore

log_paths = [u'/beholder/s61304002/encoder/log',
  u'/beholder/s61304002/encoder/x/log',
  u'/beholder/s61304002/encoder/y/log',
  u'/beholder/s61304002/log',
  u'/hsm/log',
  u'/kiln/log',
  u'/kiln/regulator/log',
  u'/log']

class ReferenceLogModelTest(unittest.TestCase):

    """Tests parsing of log paths"""
    def setUp(self):
        self.a =1
        fpath = os.path.join(iutils_testing.data_dir, 'test_video.h5')
        fp = indexer.SharedFile(fpath, mode='r')
        self.log = ReferenceLogModel(fp)
        
    def tearDown(self):
        self.log.proxy.close()       

    def test_get_log_paths(self):
        self.assertEqual(self.log.get_log_paths(), log_paths)
        
    def test_set_log_path(self):
        self.log.set_log_path('/hsm/log')
        self.assertEqual(self.log.rowCount(), 8)

        self.log.set_log_path('/beholder/s61304002/log')
        self.assertEqual(self.log.rowCount(), 24)
        
    def test_data(self):
        self.log.set_log_path('/hsm/log')
        self.assertEqual(self.log.data(self.log.index(0,0)), 1.4322144262483E9)
        self.assertEqual(self.log.data(self.log.index(0,1)), "init_acquisition isDevice False")


class OfflineLogTest(unittest.TestCase):

    """Tests parsing of log paths"""

    def test_menu(self):
        fpath = os.path.join(iutils_testing.data_dir, 'test_video.h5')

        fp = indexer.SharedFile(fpath, mode='r')
        log = fileui.OfflineLog(fp)
        log.build_menu()
        labels = [a.text() for a in log.menu.actions()]
        self.assertEqual(labels, log_paths)


if __name__ == "__main__":
    unittest.main()
