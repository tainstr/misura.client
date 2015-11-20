#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Test for thermal cycle editor"""
import unittest
from misura.client.tests import iutils_testing
from misura.client.procedure import thermal_cycle
from misura import kiln
from PyQt4 import QtGui


class Designer(unittest.TestCase):

    @unittest.skipIf(__name__ != '__main__', "should be executed only manually")
    def test(self):
        k = kiln.Kiln()
        lim = k['rateLimit']
        lim+=[[50,15],[200,20]]
        k._writeLevel = 5
        k._readLevel = 5
        call = lambda f, *ar, **kw: getattr(k, f)(*ar, **kw)
        setattr(k, 'call', call)
        tcd = thermal_cycle.ThermalCycleDesigner(k, k, force_live=True)
        tcd.remote['rateLimit'] = lim
        tcd.show()
        QtGui.qApp.exec_()

    def test_ramp_to_thermal_cycle_table(self):
        self.assertEqual([[0.0, 0], [3000.0, 1000.0]], thermal_cycle.ramp_to_thermal_cycle_curve(1000, 20))
        self.assertEqual([[0.0, 0], [2600.0, 1300.0]], thermal_cycle.ramp_to_thermal_cycle_curve(1300, 30))
        self.assertEqual([[0.0, 0], [1350.0, 1800.0]], thermal_cycle.ramp_to_thermal_cycle_curve(1800, 80))





if __name__ == "__main__":
    unittest.main(verbosity=2)
