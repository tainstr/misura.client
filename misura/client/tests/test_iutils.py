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
	
	
	def test_num_to_string(self):
		self.assertEqual("", iutils.num_to_string(""))
		self.assertEqual("23", iutils.num_to_string("23"))
		self.assertEqual("23.00", iutils.num_to_string(23))
		self.assertEqual("2374.0", iutils.num_to_string(2374))
		self.assertEqual("-2374.0", iutils.num_to_string(-2374))
		self.assertEqual("2.37E+06",iutils.num_to_string(2374000))
	
	
	def test_guess_next_name(self):
		self.assertEqual("","")
	
	
	def test_memory_check(self):
		print(iutils.memory_check())
		self.assertFalse(iutils.memory_check()[0])
		
		

if __name__ == "__main__":
	unittest.main()
