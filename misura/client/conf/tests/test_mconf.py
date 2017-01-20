#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import os
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from misura.client import conf

from misura.client.tests import iutils_testing 
from misura.client import filedata
from PyQt4 import QtGui

nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')
logging.debug('Importing', __name__)
main = __name__ == '__main__'


def setUpModule():
    logging.debug('setUpModule', __name__)


def tearDownModule():
    logging.debug('tearDownModule', __name__)



class TestTreePanel(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_proxy = filedata.getFileProxy(nativem4)
        file_proxy.load_conf()
        file_proxy.close()
        self.server = file_proxy.conf

    def test_recursiveModel(self):
        logging.debug('######## STARTING MCONF #######' * 10)
        m = conf.TreePanel(self.server.users, select=self.server.users)
        if main:
            m.show()
            QtGui.qApp.exec_()


if __name__ == "__main__":
    unittest.main()
