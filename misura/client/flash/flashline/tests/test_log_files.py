#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import numpy as np

from thegram.flashline import log_files 
from thegram.flashline.tests import testdir


class LogFiles(unittest.TestCase):
    def chk(self, name, length=0):
        t, m = log_files.parse_log_file(name)
        self.assertEqual(len(t), len(m))
        self.assertEqual(len(t), length)
        return t, m

    def test_single(self):
        tab = self.chk(testdir + 'dta/1273MO.clog', 2840)
        tab = self.chk(testdir + 'dta/1273MO.d_c', 4043)
        tab = self.chk(testdir + 'dta/1273MO.d_d', 44067)
        tab = self.chk(testdir + 'dta/1273MO.d_f', 248)
        tab = self.chk(testdir + 'dta/1273MO.d_g', 9388)
        tab = self.chk(testdir + 'dta/1273MO.d_h', 1920)
        tab = self.chk(testdir + 'dta/1273MO.d_l', 3932)
        tab = self.chk(testdir + 'dta/1273MO.d_t', 3392)
        tab = self.chk(testdir + 'dta/1273MO.d_Thread', 2)
        tab = self.chk(testdir + 'dta/1273MO.log', 55)
    
    def test_all(self):
        t, m = log_files.parse_all_logs(testdir + 'dta/')
        self.assertEqual(len(t), len(m))
        self.assertEqual(len(t), 69887)
        
    def test_differentiate_equal_times(self):
        vt = np.array([1,2,3,3,3,3,4,5,6,7,8,8,8,9,10]).astype(float)
        vt = log_files.differentiate_equal_times(vt)
        self.assertAlmostEqual(sum(vt-np.array([1,2,3,3.25,3.5,3.75,4,5,6,7,8,8.33333333,8.66666667,9,10])), 0, delta=0.00001)


if __name__ == "__main__":
    unittest.main(verbosity=2)