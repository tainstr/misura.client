#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests aButton widget."""
import unittest
from misura.canon.logger import Log as logging
from misura.client.tests import iutils_testing
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui


class aButton(unittest.TestCase):

    def setUp(self):
        self.root = option.ConfigurationProxy()

    def wgGen(self):
        self.assertTrue(self.root.has_key('test'))
        widget = widgets.build(self.root, self.root, self.root.gete('test'))
        # The current value is not initialized (gete() returns {current:None} )
        self.assertTrue(widget is not False)
        return widget

    def test(self):
        self.root.sete('test', option.ao({}, 'test', 'Button')['test'])
        # Test with short reply
        self.root['test'] = 'test text'
        widget = self.wgGen()
        msgBox = widget._msgBox()
        self.assertEqual(msgBox.informativeText(), 'test text')
        # Try with long reply
        self.root['test'] = 'test text\n' * 100
        widget.current = self.root['test']
        msgBox = widget._msgBox()
        self.assertTrue(str(msgBox.informativeText()).startswith('test text'))
        self.assertEqual(msgBox.detailedText(), self.root['test'])

        iutils_testing.show(widget, __name__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
