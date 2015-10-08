#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from misura.client.procedure.row import update_row, find_max_heating_rate



class TestTermalCycleRow(unittest.TestCase):
        
    def test_find_max_heating_rate(self):
        T = 100
        rateLimit = []
        maxHeatingRate = 100
        f =lambda: find_max_heating_rate(T, rateLimit, maxHeatingRate)
        self.assertEqual(f(), maxHeatingRate)
        rateLimit = [[50,15]]
        self.assertEqual(f(),maxHeatingRate)
        rateLimit = [[50,15],[200,20]]
        self.assertEqual(f(),20)
        T = 201
        self.assertEqual(f(), maxHeatingRate)
        T = 200
        self.assertEqual(f(), 20)
        
        
    def test_string_value_are_ignored(self):
        rows = [[0, 'any string', None, None]]
        modes = 'any mode'
        self.assertIs(
            rows[0], update_row(rows, 0, modes)[0])

    def test_no_numeric_values_found(self):
        modes = 'any mode'
        rows = [[1, 2, 3, 4], [None, 'any string', None, None],
                [None, 'any string', None, None]]

        self.assertIs(
            rows[0], update_row(rows, 0, modes)[0])

    def test_rate_mode_with_0_eating_rate(self):
        modes = 'ramp'
        rows = [[0, 0, 0, 0], [0, 100, 0, 0]]

        self.assertEqual(
            [0, 0, 0, 0], update_row(rows, 1, modes)[0])

    def test_rate_mode_with_heating_rate_set(self):
        modes = 'ramp'
        rows = [[0, 0, 0, 0], [0, 100, 20, 0]]
        self.assertEqual(
            [5, 100, 20, 5], update_row(rows, 1, modes)[0])

        rows = [[0, 0, 0, 0], [5, 200, 20, 5], [0, 200, 0, 0]]
        self.assertEqual(
            [5, 200, 0, 0], update_row(rows, 2, modes)[0])

        rows = [[0, 0, 0, 0], [5, 100, 20, 5], [5, 200, 20, 0]]
        self.assertEqual(
            [10, 200, 20, 5], update_row(rows, 2, modes)[0])

    def test_time_mode(self):
        modes = 'points'
        rows = [[0, 30, 0, 0], [0, 100, 0, 0]]
        self.assertEqual(
            [0, 100, 0, 0], update_row(rows, 1, modes)[0])

        rows = [[0, 30, 0, 0], [10, 100, 0, 0]]
        self.assertEqual(
            [10, 100, 7, 10], update_row(rows, 1, modes)[0])

    def test_duration_mode(self):
        modes = 'dwell'

        rows = [[0, 30, 0, 0], [0, 30, 0, 0]]
        self.assertEqual(
            [0, 30, 0, 0], update_row(rows, 1, modes)[0])

        rows = [[0, 30, 0, 0], [0, 30, 0, 10]]
        self.assertEqual(
            [10, 30, 0, 10], update_row(rows, 1, modes)[0])

    def test_duration_should_not_change_when_rate_is_set_to_zero_and_temperature_does_not_change(self):
        modes = 'ramp'

        rows = [[0, 30, 0, 0], [10, 30, 0, 10]]

        self.assertEqual(
            [10, 30, 0, 10], update_row(rows, 1, modes)[0])

    def test_when_rate_is_set_to_zero_temperature_should_become_equal_to_previous_row(self):
        modes = 'ramp'

        rows = [[0, 40, 0, 0], [10, 30, 0, 10]]
        self.assertEqual(
            [10, 40, 0, 10], update_row(rows, 1, modes)[0])

    def test_when_rate_is_set_to_zero_temperature_should_become_equal_to_previous_non_event_row(self):
        modes = 'ramp'

        rows = [[0, 40, 0, 0], [0, '>any event', 0, 0], [10, 30, 0, 10]]
        self.assertEqual(
            [10, 40, 0, 10], update_row(rows, 2, modes)[0])

    def test_when_rate_is_set_to_zero_not_in_ramp_mode_temperature_should_not_be_changed(self):
        modes = 'points'

        rows = [[0, 40, 0, 0], [0, 30, 0, 10]]
        self.assertEqual(
            [0, 30, 0, 0], update_row(rows, 1, modes)[0])
        
    def test_rate_correction(self):
        modes = 'points'
        rows = [[0.,0.,0,0],
                [10., 1000., 100, 10],
                [20., 1500., 50, 10]]
        new_row, time_correction = update_row(rows, 1, modes, maxRate = 100)
        self.assertEqual(new_row, rows[1])
        self.assertEqual(time_correction, 0)
        
        new_row, time_correction = update_row(rows, 1, modes, maxRate = 50)
        self.assertEqual(time_correction, 10)
        self.assertEqual(new_row, [20, 1000, 50, 20] )
        
        
        
        

if __name__ == "__main__":
    unittest.main(verbosity=2)
