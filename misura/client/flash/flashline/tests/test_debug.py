#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest

from misura.client.flash.flashline import debug_table
from misura.client.flash.flashline.tests import testdir


class DebugTable(unittest.TestCase):

    def test_debug_table(self):
        table, zerotime = debug_table.debug_table(testdir + 'dta/1273MO.d_t')
        print(table, zerotime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
