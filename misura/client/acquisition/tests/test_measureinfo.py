#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import functools

from misura import utils_testing
from misura.client.tests import iutils_testing

from misura.client.acquisition import measureinfo
from misura import instrument

from test_controls import Parent
from misura.canon import option
from misura import kiln, flex

from PyQt4 import QtGui,QtCore


class MeasureInfo(unittest.TestCase):
	def setUp(self):
		self.server=utils_testing.dummyServer(flex.Flex, kiln.Kiln)
		self.remote_instrument = self.server.flex

		proxy=option.ConfigurationProxy(self.server.tree()[0])
		proxy._parent=option.ConfigurationProxy(self.server.tree()[0])
		self.measure_info = measureinfo.MeasureInfo(proxy.flex)
		
	def check_tabs(self):
		number_of_samples = self.remote_instrument.measure['nSamples']
		self.assertEqual(self.measure_info.count(), 4 + number_of_samples)

				
	def test_tabs_for_two_samples(self):
		self.measure_info.remote.measure['nSamples'] = 2
		self.measure_info.refreshSamples()
		self.check_tabs()

	def test_tabs_for_one_samples(self):
		self.measure_info.remote.measure['nSamples'] = 1
		self.measure_info.refreshSamples()
		self.check_tabs()
			
		
if __name__ == "__main__":
	unittest.main() 
	
