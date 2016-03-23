#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import os
from misura.canon.logger import Log as logging

from misura import server
from misura.client import conf
from misura.client import filedata

from misura.client.tests import iutils_testing as iut
from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)
main = __name__ == '__main__'


def setUpModule():
    logging.debug('%s %s', 'setUpModule', __name__)


def tearDownModule():
    logging.debug('%s %s', 'tearDownModule', __name__)

# nativem4=os.path.join(iut.data_dir,'post_m3.h5')


#@unittest.skip('')
class TestTreePanel(unittest.TestCase):
    #	@unittest.skip('')

    def test_recursiveModel(self):
        s = server.MainServer()
        logging.debug('%s', '######## STARTING MCONF #######' * 10)
        m = conf.TreePanel(s.users, select=s.users)
        if main:
            m.show()
            QtGui.qApp.exec_()


if __name__ == "__main__":
    unittest.main()
