#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import os
import numpy
from misura.client import filedata
from misura.client import plugin
from misura.client.plugin.RemoveGapsPlugin import remove_gaps_from

class RemoveGapsPlugin(unittest.TestCase):

	def test_remove_single_gap(self):
		input_data =      numpy.array([1,2,3,4,5,6,100,101,102,10,11,12])
		expected_output = numpy.array([1,2,3,4,5,6,6  ,7  ,8  ,8 ,9 ,10])

		actual_output = remove_gaps_from(input_data, 10)

		self.assertIsNot(actual_output, input_data)

		for index, output_element in enumerate(actual_output):
			self.assertEqual(output_element, expected_output[index])

	def test_remove_multiple_gaps(self):
		input_data =      numpy.array([10,20,30,40,50,60,5 ,15,25,35,110,120,130,200,210,220,170,180])
		expected_output = numpy.array([10,20,30,40,50,60,60,70,80,90,90 ,100,110,110,120,130,130,140])

		actual_output = remove_gaps_from(input_data, 10)

		self.assertIsNot(actual_output, input_data)

		for index, output_element in enumerate(actual_output):
			self.assertEqual(output_element, expected_output[index])

if __name__ == "__main__":
	unittest.main(verbosity=2)  
