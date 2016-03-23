#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
from misura.client.acquisition import selector
from PyQt4 import QtGui, QtCore
from misura.client.tests import iutils_testing


class Parent(QtGui.QWidget):
    ok = False
    ins = False

    def newTest(self): self.ok = True

    def setInstrument(self, ins): self.ins = ins


class InstrumentSelector(unittest.TestCase):

    def setUp(self):
        # Fire instantiate the full server with all defined instruments
        self.server = None#server.MainServer()
        self.rem = self.server.instruments[0]
        self.rem.parent = lambda: self.server
        self.parent = Parent()
        self.parent.server = self.server
        self.sel = selector.InstrumentSelector(
            self.parent, self.parent.setInstrument)

    def test_init(self):
        lst = self.server['instruments']
        n = len(lst)
        self.assertEqual(n, self.sel.lay.count())
        # Check for title correspondence
        for i in range(self.sel.lay.count()):
            btn = self.sel.lay.itemAt(i)
            self.assertNotEqual(btn, 0)
            btn = btn.widget()
            self.assertNotEqual(btn, 0)
            self.assertEqual(btn.text(), lst[i][0])


if __name__ == "__main__":
    unittest.main()
