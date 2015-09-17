#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests DataDecoder"""
import unittest

from misura.client.filedata import axis_selection


class AxisSelection(unittest.TestCase):
	def test_get_temperature_path_of_sample_with_path(self):
	    	sample_path = "0:/path/XXX/fullpath/XXX"
	    	expected_sample_temperature_path = "0:/path/XXX/fullpath/T"

	    	actual_sample_temperature_path = axis_selection.get_temperature_of_sample_with_path(sample_path)

	    	self.assertEqual(expected_sample_temperature_path, actual_sample_temperature_path)


	def test_best_x_is_time(self):
	   	page = "/time/..."
	   	prefix = "a_prefix:"

	   	self.assertEqual("a_prefix:t", axis_selection.get_best_x_for("any path", prefix, "any data", page))

	def test_best_x_is_kiln_temperature(self):
		page = "a no time page"
		data = {}
		prefix = "a_prefix:"

		self.assertEqual("a_prefix:kiln/T",\
			axis_selection.get_best_x_for("a path not in data", prefix, data, page))

	def test_best_x_is_sample_temperature(self):
		page = "a no time page"
		data = {"a/path/for/sample/T": "some data"}
		prefix = "a_prefix:"
		path = "a/path/for/sample/key"

		self.assertEqual("a/path/for/sample/T",\
			axis_selection.get_best_x_for(path, prefix, data, page))







if __name__ == "__main__":
    unittest.main(verbosity=2)
