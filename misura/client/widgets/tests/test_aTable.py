#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests aTable widget."""
import unittest
from misura.client.tests import iutils_testing

from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui, QtCore


class aTable(unittest.TestCase):

    def setUp(self):
        self.root = option.ConfigurationProxy()

    def wgGen(self):
        self.assertTrue(self.root.has_key('test'))
        widget = widgets.build(self.root, self.root, self.root.gete('test'))
        self.assertTrue(widget is not False)
        return widget

    def test(self):
        self.root.sete('test', option.ao({}, 'test', 'Table', [
                       [('ColStr', 'String'), ('ColInt', 'Integer'), ('ColFloat', 'Float')], ['pippo', 1, 0.5]])['test'])
        widget = self.wgGen()

        iutils_testing.show(widget, __name__)

if __name__ == "__main__":
    unittest.main(verbosity=2)
