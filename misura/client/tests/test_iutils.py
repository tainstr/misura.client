#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from misura.client import iutils


class UtilsTests(unittest.TestCase):
	def test_long_names_shorten(self):
	    self.assertEqual("", iutils.shorten(""))
	    self.assertEqual("any short name", iutils.shorten("any short name"))
	    self.assertEqual("abc...xyz", iutils.shorten("abcdefghixyz", 6))
	    self.assertEqual("abcde...vwxyz", iutils.shorten("abcdefghivwxyz", 10))
	    self.assertEqual("C://very long f.../measurefile.h5",
	    	iutils.shorten("C://very long file name that ends with /measurefile.h5"))

if __name__ == "__main__":
    unittest.main()
