#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests DataDecoder"""
import unittest

from misura.client.filedata import axis_selection


class AxisSelection(unittest.TestCase):

    def test_get_neighbor_x(self):
        sample_path = "0:/path/XXX/fullpath/XXX"
        expected_sample_temperature_path = "0:/path/XXX/fullpath/T"

        actual_sample_temperature_path = axis_selection.get_neighbor_x(
            sample_path)

        self.assertEqual(
            expected_sample_temperature_path, actual_sample_temperature_path)

    def test_best_x_is_time(self):
        page = "/time/..."
        prefix = "a_prefix:"

        self.assertEqual("a_prefix:t", axis_selection.get_best_x_for(
            "any path", prefix, "any data", page))

    def test_best_x_is_kiln_temperature(self):
        page = "a no time page"
        data = {}
        prefix = "a_prefix:"

        self.assertEqual("a_prefix:kiln/T",
                         axis_selection.get_best_x_for("a path not in data", prefix, data, page))

    def test_best_x_is_sample_temperature(self):
        page = "a no time page"
        data = {"a/path/for/sample/T": "some data"}
        prefix = "a_prefix:"
        path = "a/path/for/sample/key"

        self.assertEqual("a/path/for/sample/T",
                         axis_selection.get_best_x_for(path, prefix, data, page))

    def test_is_temperature(self):
        self.assertFalse(axis_selection.is_temperature("0:/hsm/sample0"))
        self.assertTrue(axis_selection.is_temperature("anything you want /T"))
        self.assertTrue(
            axis_selection.is_temperature("anything you want kiln/T and whatever"))
        self.assertFalse(
            axis_selection.is_temperature("anything you want kiln/"))
        self.assertFalse(
            axis_selection.is_temperature("anything you want /T and something else"))

    def test_kiln_temperature_for(self):
        self.assertEqual("something:kiln/T",
                         axis_selection.kiln_temperature_for("something:somthing/else"))

    def test_is_calibratable(self):
        self.assertFalse(
            axis_selection.is_calibratable("0:something:somthing/else"))
        self.assertTrue(
            axis_selection.is_calibratable("0:horizontal/sample0/d"))
        self.assertTrue(axis_selection.is_calibratable("1:vertical/sample0/d"))
        self.assertFalse(
            axis_selection.is_calibratable("3:vertical/sample0/d/something/else"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
