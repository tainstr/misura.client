#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
from nose.plugins.skip import SkipTest


from misura.client.acquisition import menubar
from test_controls import Parent


from PyQt4 import QtGui, QtCore

class Parent(QtGui.QWidget):
    fixedDoc = False
    measureDock = False
    snapshotsDock = False
    graphWin = False
    tableWin = False
    logDock = False

    def setInstrument(self, instrument): self.ins = instrument

    def init_instrument(self):
        return True

    def delayed_start(self):
        return True

@SkipTest #Needs the server, so it should not be run automatically
class MenuBar(unittest.TestCase):

    def setUp(self):
        from misura import instrument
        from misura import server

        self.root = server.MainServer()
        self.remote_instrument = self.root.instruments[0]
        self.remote_instrument.parent = lambda: self.root
        self.remote_instrument.server = self.root
        self.parent = Parent()
        self.menu_bar = menubar.MenuBar(self.root, self.parent)

    def test_init(self):
        number_of_instruments = len(self.root.instruments)

        self.assertEqual(
            len(self.menu_bar.lstInstruments), number_of_instruments)
        self.assertEqual(
            len(self.menu_bar.instruments.actions()), number_of_instruments)

    def test_setInstrument(self):
        self.menu_bar.setInstrument(self.remote_instrument, self.root)

    def test_updateActions(self):
        self.menu_bar.updateActions()


if __name__ == "__main__":
    unittest.main()
