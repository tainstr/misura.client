#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from misura.client.graphics.thermal_cycle_row import ThermalCycleRow

class TestPlot(unittest.TestCase):
	def test_string_value_are_ignored(self):
		thermal_cycle_row = ThermalCycleRow()
		rows = [[None, 'any string']]

		self.assertIs(rows[0], thermal_cycle_row.update_row(rows, 0, 'any mode'))


if __name__ == "__main__":
	unittest.main(verbosity=2)  