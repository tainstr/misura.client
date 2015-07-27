#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests aString widget."""
import unittest
from misura.client import widgets
from misura.client.tests import iutils_testing
from misura.canon import option
from PyQt4 import QtGui, QtCore


class aString(unittest.TestCase):

    def setUp(self):
        self.root = option.ConfigurationProxy()

    def wgGen(self):
        self.assertTrue(self.root.has_key('test'))
        widget = widgets.build(self.root, self.root, self.root.gete('test'))
        self.assertTrue(widget is not False)
        return widget

    def test_String(self):
        self.root.sete('test', option.ao({}, 'test', 'String')['test'])
        widget = self.wgGen()
        iutils_testing.show(widget, __name__)

    def test_TextArea(self):
        self.root.sete('test', option.ao({}, 'test', 'TextArea')['test'])
        widget = self.wgGen()
        iutils_testing.show(widget, __name__)

if __name__ == "__main__":
    unittest.main(verbosity=2)
