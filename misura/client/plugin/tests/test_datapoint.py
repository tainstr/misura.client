#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing plugin/CurveOperationPlugin.py plugin."""
import unittest
from nose.plugins.skip import SkipTest
from misura.canon.logger import Log as logging

import numpy as np

import veusz.document as document
import veusz.widgets
import veusz.plugins

from misura.client.plugin import datapoint

app = False

@unittest.skip("don't know how to make this work...")
class DataPoint(unittest.TestCase):

    """Tests the CurveOperationPlugin."""
    density = 1
    delta = None

    def setUp(self):
        self.dp = datapoint.DataPoint(None)
        self.assertEqual(self.dp.settings.search, 'Nearest (Fixed X)')
        self.delta = None

    def search(self, start=None, expect=90, delta=None):
        if not delta:
            delta = self.delta
            if not delta:
                delta = 3 * self.density
        expect *= self.density
        if start is not None:
            start *= self.density
            self.dp.point_index = start
            self.dp.x = self.dp.xData[self.dp.point_index]
            self.dp.y = self.dp.yData[self.dp.point_index]
        logging.debug(
            '%s %s %s %s', 'starting from', self.dp.point_index, self.dp.x, self.dp.y)
        self.assertTrue(self.dp.critical_search(self.dp.settings.search))
        logging.debug(
            '%s %s %s %s', 'ending in', self.dp.point_index, self.dp.x, self.dp.y)
        self.assertAlmostEqual(self.dp.point_index, expect, delta=delta)

    def critical_search(self, delta=None):
        dp = self.dp
        # Initial situation
        self.dp.settings.search = 'None'
        self.dp.xRange = self.dp.xData.max() - self.dp.xData.min()
        self.dp.yRange = self.dp.yData.max() - self.dp.yData.min()
        self.assertFalse(dp.critical_search(self.dp.settings.search))

        # Range is too small! Going towards the nearest maximum, but not
        # reaching
        dp.settings.search = 'Maximum'
        dp.settings.searchRange = 10
        self.search(start=120, expect=115)

        # Increase the range, reach real max
        dp.settings.searchRange = 180
        self.search(expect=90)  # continue
        # Now invert the search
        dp.settings.search = 'Minimum'
        self.search(start=85, expect=0)

        # Stationary: maximum OR minimum defined by 1 derivative
        dp.settings.search = 'Stationary'
        # fall onto 90 max
        self.search(start=110, expect=90)
        # fall onto 270 min
        self.search(start=195, expect=270)

        # Inflection
        dp.settings.search = 'Inflection'
        self.search(start=140, expect=180)

    reps = (117, 105, 100, 95, 75, 40, 190, 210, 261, 155, 171)

    def rep(self):
        """Repeat some points to test zero xData derivative masking"""
        for i in self.reps:
            i *= self.density
            self.dp.xData[i] = self.dp.xData[i + 1]
            self.dp.yData[i] = self.dp.yData[i + 1]

    def test_critical_search_mono(self):
        """Critical search with monotonic xData"""
        self.dp.xData = np.arange(360 * self.density + 1) / self.density
        self.dp.yData = np.sin(2 * np.pi * self.dp.xData / 360.)
        self.critical_search()

        # Introduce repeated points
        self.rep()
        self.critical_search()

    def test_critical_search_nonmono(self):
        """Critical search with non-monotonic xData"""
        x0 = np.arange(1 + 360 * self.density) / self.density

        def xData(d=180, noise=0):
            x1 = x0.copy()
            s = 1. / self.density
            r = np.cumsum(np.ones(len(x1) - d))
            x1[d:] = x1[d + 1] - r
            if noise:
                ns = np.random.rand(len(x1))
                ns[ns < 0.1] = 0
                x1 += ns * noise
            return x1

        self.dp.xData = xData(180)
        self.dp.yData = np.sin(2 * np.pi * x0 / 360.)

        self.critical_search()

        # Introduce repeated points
        self.rep()
        self.critical_search()

        # Introduce random noise on xData
        self.dp.xData = xData(180, noise=2)
        self.dp.yData = np.sin(2 * np.pi * x0 / 360.)
        self.rep()
        self.delta = 10
        self.critical_search()


if __name__ == "__main__":
    unittest.main(verbosity=2)
