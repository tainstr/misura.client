#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing CalibrationFactorPlugin."""
import unittest
from misura.client.plugin import utils
import numpy as np


class TestPluginUtils(unittest.TestCase):

    """Tests the CalibrationFactorPlugin"""

    def test__update_filter(self):
        old = np.array([0,1,4,8,10,11])
        new = np.array([0,2,8,9,10])
        res = utils._update_filter(new, old)
        self.assertEqual(list(res), list(np.sort([0,1,4, 8, 10,11, 
                                                  2, 5, 14, 15, 16])))
        res1 = utils._update_filter(np.array([1,3,5]), res)
        self.assertEqual(list(res1), list(np.sort([0,1,4, 8, 10,11, 
                                                  2, 5, 14, 15, 16,
                                                  6, 9,13])))
        


if __name__ == "__main__":
    unittest.main(verbosity=2)