#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import os
from misura.client.tests import iutils_testing

from misura.client.conf import devtree
from misura.client import filedata

app = False

nativem4 = os.path.join(iutils_testing.data_dir, 'measure.h5')


class RecursiveModel(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_proxy = filedata.getFileProxy(nativem4)
        file_proxy.load_conf()
        file_proxy.close()
        self.server = file_proxy.conf

    def test_recursiveModel(self):
        m = devtree.recursiveModel(self.server)

# TODO: test su fileproxy!


class ServerModel(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_proxy = filedata.getFileProxy(nativem4)
        file_proxy.load_conf()
        file_proxy.close()
        self.server = file_proxy.conf

    def setUp(self):
        self.m = devtree.recursiveModel(self.server)

    def test_init(self):
        mod = devtree.ServerModel(self.server)


if __name__ == "__main__":
    unittest.main()
