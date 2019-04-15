#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from misura.client.flash.flashline import results
from misura.client.flash.flashline.tests import testdir


class Results(unittest.TestCase):

    def test_all_table(self):
        table = results.all_table(testdir + 'MO6_1/results.all')
        # N rows
        self.assertEqual(len(table), 15)
        # N columns
        self.assertEqual(len(table[0]), 15)
        # All columns must have equal rows!
        lengths = set([len(v) for v in table])
        self.assertEqual(len(lengths), 1)

    def test_segment_temperature_values(self):
        clt = results.segment_temperature_values(testdir + 'MO6_1/results.clt')
        deg = results.segment_temperature_values(testdir + 'MO6_1/results.deg')
        cow = results.segment_temperature_values(testdir + 'MO6_1/results.cow')
        hft = results.segment_temperature_values(testdir + 'MO6_1/results.hft')
        gdf = results.segment_temperature_values(testdir + 'MO6_1/results.gdf')

        # All tables should have equal rows (representing segments)
        rows = [len(tab) for tab in (clt, deg, cow, hft, gdf)]
        self.assertEqual(len(set(rows)), 1)
        # And equal cols (except gdf)
        cols = [len(tab[0]) for tab in (clt, deg, cow, hft)]
        self.assertEqual(len(set(cols)), 1)
        self.assertEqual(len(gdf[0]), 9)
        
    def test_results_cryo(self):
        table = results.all_table(testdir + 'results_cryo.all')
        self.assertEqual(len(table), 45)


if __name__ == "__main__":
    unittest.main(verbosity=2)
