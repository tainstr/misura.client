#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests role selector widget."""
import unittest
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui, QtCore

from misura.client.tests import iutils_testing
main = __name__ == '__main__'

# TODO: generalize a widget testing  framework


ev = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPoint(0, 0), QtCore.QPoint(0, 0),
                       QtCore.Qt.NoButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier)


class FocusableSlider(unittest.TestCase):

    def setUp(self):
        self.wg = widgets.FocusableSlider()

    def tearDown(self):
        print 'teardown'
        self.wg.close()

    def test_set_paused(self):
        self.assertFalse(self.wg.paused)
        self.assertTrue(self.wg.set_paused(True))
        self.assertTrue(self.wg.paused)
        self.assertTrue(self.wg.set_paused(False))
        self.assertFalse(self.wg.paused)
        self.assertFalse(self.wg.set_paused(False))

    def test_mousePressEvent(self):
        self.assertFalse(self.wg.paused)
        self.wg.mousePressEvent(ev)
        self.assertTrue(self.wg.paused)
        self.wg.mouseReleaseEvent(ev)
        self.assertFalse(self.wg.paused)

    def test_mouseDoubleClickEvent(self):
        self.assertFalse(self.wg.zoomed)
        self.wg.mouseDoubleClickEvent(ev)
        self.assertTrue(self.wg.zoomed)
        self.wg.mouseDoubleClickEvent(ev)
        self.assertFalse(self.wg.zoomed)


class aNumber(unittest.TestCase):

    def setUp(self):
        self.root = option.ConfigurationProxy()

    def wgGen(self):
        self.assertTrue(self.root.has_key('Test'))
        w = widgets.build(self.root, self.root, self.root.gete('Test'))
        # The current value is not initialized (gete() returns {current:None} )
        self.assertTrue(w is not False)
        return w

    def test_integer(self):
        self.root.sete('Test', option.ao({}, 'Test', 'Integer')['Test'])
        w = self.wgGen()
        self.assertEqual(w.current, 0)
        self.assertFalse(w.slider)
        iutils_testing.show(w, __name__)

    def test_float(self):
        self.root.sete('Test', option.ao({}, 'Test', 'Float')['Test'])
        w = self.wgGen()
        self.assertEqual(w.current, 0)
        self.assertFalse(w.slider)

    def test_MIN_MAX_int(self):
        self.root.sete(
            'Test', option.ao({}, 'Test', 'Integer', 59298, min=0,  max=59298, step=388)['Test'])
        w = self.wgGen()
        self.assertEqual(w.current, 59298)
        self.assertTrue(w.slider)
        iutils_testing.show(w, __name__)
        
    def test_MIN_MAX_dbl(self):
        self.root.sete(
            'Test', option.ao({}, 'Test', 'Float', 5, min=-10,  max=10)['Test'])
        w = self.wgGen()
        self.assertEqual(w.current, 5)
        self.assertTrue(w.slider)
        iutils_testing.show(w, __name__)

    def test_Properties(self):
        self.root.sete(
            'Test', option.ao({}, 'Test', 'Float', current=120, unit='second', precision=4)['Test'])
        w = self.wgGen()
        w.lay.addWidget(w.label_widget)
        iutils_testing.show(w, __name__)

    def test_units(self):
        self.root.sete(
            'Test', option.ao({}, 'Test', 'Float', units='second')['Test'])
        w = self.wgGen()
        self.assertEqual(w.current, 0)
        self.assertFalse(w.slider)


if __name__ == "__main__":
    unittest.main(verbosity=2)
