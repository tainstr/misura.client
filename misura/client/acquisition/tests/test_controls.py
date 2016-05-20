#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest

from misura.client.tests import iutils_testing

from misura.client.acquisition import controls
from PyQt4 import QtGui


class DummyMeasureTab():

    def checkCurve(self):
        return True


class DummyDock():

    def widget(self):
        return DummyMeasureTab()


class DummyOutFile():

    def close(self):
        return True


class Parent(QtGui.QWidget):
    measureDock = DummyDock()
    fixedDoc = False

@unittest.skip("Needs the server, so it should not be run automatically")
class Controls(unittest.TestCase):

    def setUp(self):
        from misura import utils_testing
        from misura import instrument
        self.server = utils_testing.dummyServer()
        self.remote_instrument = instrument.Instrument(self.server)
        self.remote_instrument.start_acquisition = lambda: self.server.set(
            'isRunning', True)
        self.remote_instrument.parent = lambda: self.server
        self.remote_instrument.outFile = DummyOutFile()
        self.parent = Parent()
        self.ctrl = controls.Controls(self.remote_instrument, self.parent)
        self.ctrl.mute = True

    def tearDown(self):
        self.remote_instrument.stop_acquisition(False)

    def check_act(self):
        self.assertEqual(
            self.ctrl.startAct.isEnabled(), not self.server['isRunning'])
        self.assertEqual(
            self.ctrl.stopAct.isEnabled(), self.server['isRunning'])

    def test_init(self):
        self.check_act()

    def test_start(self):
        class DummtTasks():

            @classmethod
            def jobs(self, n, msg):
                return True

            @classmethod
            def setFocus(self):
                return True

            @classmethod
            def done(self, arg):
                return True
        setattr(controls.Controls, "tasks", DummtTasks)

        self.ctrl._start()

        self.assertTrue(
            self.server['isRunning'], "Server should be running, but it's not.")

    def test_stop(self):
        self.test_start()
        self.ctrl._stop()
        self.assertFalse(self.server['isRunning'])


@unittest.skipIf(__name__ != '__main__', 'Non interactive.')
class HuControl(unittest.TestCase):
    __test__ = False
    def test_hu(self):
        utils_testing.parallel(1)
        self.server = utils_testing.dummyServer()
        self.rem = instrument.Instrument(self.server)
# 		self.rem.start_acquisition=functools.partial(self.server.set,'isRunning',True)
        self.rem.parent = lambda: self.server
        self.parent = Parent()
        self.ctrl = controls.Controls(self.rem, self.parent)
# 		self.ctrl.mute=True
        mw = QtGui.QMainWindow()
        mw.addToolBar(self.ctrl)
        mw.show()
        QtGui.qApp.exec_()
        utils_testing.parallel(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
