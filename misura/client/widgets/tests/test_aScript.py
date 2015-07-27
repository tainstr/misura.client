# -*- coding: utf-8 -*-
#!/usr/bin/python
"""Tests aScript widget."""
import unittest
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui, QtCore
from misura.client.tests import iutils_testing

main = __name__ == '__main__'

# TODO: generalize a widget testing  framework


class aScript(unittest.TestCase):

    def setUp(self):
        self.root = option.ConfigurationProxy()

    def wgGen(self):
        self.assertTrue(self.root.has_key('test'))
        widget = widgets.build(self.root, self.root, self.root.gete('test'))
        self.assertTrue(widget is not False)
        return widget

    def test_String(self):
        self.root.sete('test', option.ao({}, 'test', 'Script')['test'])
        widget = self.wgGen()

        iutils_testing.show(widget, __name__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
