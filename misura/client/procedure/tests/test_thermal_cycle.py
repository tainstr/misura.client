#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Test for thermal cycle editor"""
import unittest
from misura.client.tests import iutils_testing
from misura.client.procedure import thermal_cycle
from PyQt4 import QtGui

from nose.tools import assert_equals


class Designer(unittest.TestCase):

    @unittest.skipIf(__name__ != '__main__', "should be executed only manually")
    def test(self):
        from misura import kiln

        k = kiln.Kiln()
        lim = k['rateLimit']
        lim+=[[50,15],[200,20]]
        k._writeLevel = 5
        k._readLevel = 5
        k.measure._readLevel = 5
        call = lambda f, *ar, **kw: getattr(k, f)(*ar, **kw)
        setattr(k, 'call', call)
        tcd = thermal_cycle.ThermalCycleDesigner(k, k, force_live=True)
        tcd.remote['rateLimit'] = lim
        tcd.show()
        QtGui.qApp.exec_()

    def test_ramp_to_thermal_cycle_table(self):
        assert_equals([[0.0, 0], [3000.0, 1000.0]],
                      thermal_cycle.ramp_to_thermal_cycle_curve(1000, 20))
        assert_equals([[0.0, 0], [2600.0, 1300.0]],
                      thermal_cycle.ramp_to_thermal_cycle_curve(1300, 30))
        assert_equals([[0.0, 0], [1350.0, 1800.0]],
                      thermal_cycle.ramp_to_thermal_cycle_curve(1800, 80))

    def test_steps_template_to_thermal_cycle_curve(self):
        no_steps = {
            'heatingRate': 20,
            'numberOfSteps': 1,
            'stasisDuration': 120,
            'stepsDeltaT': 10,
            'firstStepTemperature': 1000
        }
        assert_equals([[0.0, 0], [3000.0, 1000], [3120.0, 1000]],
                      thermal_cycle.steps_template_to_thermal_cycle_curve(no_steps))

        no_steps2 = {
            'heatingRate': 60,
            'firstStepTemperature': 1200,
            'numberOfSteps': 1,
            'stepsDeltaT': 10,
            'stasisDuration': 120
        }
        assert_equals([[0.0, 0], [1200.0, 1200], [1320.0, 1200]],
                      thermal_cycle.steps_template_to_thermal_cycle_curve(no_steps2))

        one_step = {
            'heatingRate': 60,
            'firstStepTemperature': 1200,
            'numberOfSteps': 1,
            'stepsDeltaT': 120,
            'stasisDuration': 100
        }
        assert_equals([[0.0, 0], [1200.0, 1200], [1300.0, 1200]],
                      thermal_cycle.steps_template_to_thermal_cycle_curve(one_step))

        two_steps = {
            'heatingRate': 60,
            'firstStepTemperature': 1200,
            'numberOfSteps': 2,
            'stasisDuration': 120,
            'stepsDeltaT': 120
        }
        assert_equals([[0.0, 0], [1200.0, 1200], [1320.0, 1200], [1440, 1320], [1560, 1320]],
                      thermal_cycle.steps_template_to_thermal_cycle_curve(two_steps))


    def test_progress_bar_position(self):
        all_segments = [
            [[0.0, 0], [750.0, 1000]],
            [[750.0, 1000], [1350.0, 1000], [1365.0, 1020]],
            [[1365.0, 1020], [1965.0, 1020]]
        ]

        kiln = {
            'segments': all_segments,
            'segmentPos': 1
        }

        assert_equals(750.0 * 0.5 / 100. / 60.,
                      thermal_cycle.get_progress_time_for(0.5, kiln))


        kiln['segmentPos'] = 2
        assert_equals(750.0 + (1365.0 - 750.0) * 0.4 / 100. / 60.,
                      thermal_cycle.get_progress_time_for(0.4, kiln))

        kiln['segmentPos'] = 3
        assert_equals(1365.0 + (1965.0 - 1365.0) * 0.3 / 100. / 60.,
                      thermal_cycle.get_progress_time_for(0.3, kiln))



if __name__ == "__main__":
    unittest.main(verbosity=2)
