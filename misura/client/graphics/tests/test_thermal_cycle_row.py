#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from misura.client.graphics.thermal_cycle_row import ThermalCycleRow


class TestTermalCycleRow(unittest.TestCase):

    def setUp(self):
        self.thermal_cycle_row = ThermalCycleRow()

    def test_string_value_are_ignored(self):
        rows = [[None, 'any string', None, None]]

        self.assertIs(
            rows[0], self.thermal_cycle_row.update_row(rows, 0, 'any mode'))

    def test_no_numeric_values_found(self):
        rows = [[1, 2, 3, 4], [None, 'any string', None, None],
                [None, 'any string', None, None]]

        self.assertIs(
            rows[0], self.thermal_cycle_row.update_row(rows, 0, 'any mode'))

    def test_rate_mode_with_0_eating_rate(self):
        time_mode = 'ramp'
        rows = [[0, 0, 0, 0], [0, 100, 0, 0]]

        self.assertEqual(
            [0, 0, 0, 0], self.thermal_cycle_row.update_row(rows, 1, time_mode))

    def test_rate_mode_with_eating_rate_set(self):
        time_mode = 'ramp'
        rows = [[0, 0, 0, 0], [0, 100, 20, 0]]
        self.assertEqual(
            [5, 100, 20, 5], self.thermal_cycle_row.update_row(rows, 1, time_mode))

        rows = [[0, 0, 0, 0], [5, 200, 20, 5], [0, 200, 0, 0]]
        self.assertEqual(
            [5, 200, 0, 0], self.thermal_cycle_row.update_row(rows, 2, time_mode))

        rows = [[0, 0, 0, 0], [5, 100, 20, 5], [5, 200, 20, 0]]
        self.assertEqual(
            [10, 200, 20, 5], self.thermal_cycle_row.update_row(rows, 2, time_mode))

    def test_time_mode(self):
        time_mode = 'points'
        rows = [[0, 30, 0, 0], [0, 100, 0, 0]]
        self.assertEqual(
            [0, 100, 0, 0], self.thermal_cycle_row.update_row(rows, 1, time_mode))

        rows = [[0, 30, 0, 0], [10, 100, 0, 0]]
        self.assertEqual(
            [10, 100, 7, 10], self.thermal_cycle_row.update_row(rows, 1, time_mode))

    def test_duration_mode(self):
        time_mode = 'dwell'

        rows = [[0, 30, 0, 0], [0, 30, 0, 0]]
        self.assertEqual(
            [0, 30, 0, 0], self.thermal_cycle_row.update_row(rows, 1, time_mode))

        rows = [[0, 30, 0, 0], [0, 30, 0, 10]]
        self.assertEqual(
            [10, 30, 0, 10], self.thermal_cycle_row.update_row(rows, 1, time_mode))

    def test_duration_should_not_change_when_rate_is_set_to_zero_and_temperature_does_not_change(self):
        time_mode = 'ramp'

        rows = [[0, 30, 0, 0], [10, 30, 0, 10]]

        self.assertEqual(
            [10, 30, 0, 10], self.thermal_cycle_row.update_row(rows, 1, time_mode))

    def test_when_rate_is_set_to_zero_temperature_should_become_equal_to_previous_row(self):
        time_mode = 'ramp'

        rows = [[0, 40, 0, 0], [10, 30, 0, 10]]
        self.assertEqual(
            [10, 40, 0, 10], self.thermal_cycle_row.update_row(rows, 1, time_mode))

    def test_when_rate_is_set_to_zero_not_in_ramp_mode_temperature_should_not_be_changed(self):
        time_mode = 'points'

        rows = [[0, 40, 0, 0], [0, 30, 0, 10]]
        self.assertEqual(
            [0, 30, 0, 0], self.thermal_cycle_row.update_row(rows, 1, time_mode))

if __name__ == "__main__":
    unittest.main(verbosity=2)
