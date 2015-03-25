#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Unif conversion module"""
import unittest
import sys
import os
from misura.client import units
from PyQt4 import QtGui
app=False

print 'Importing',__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	app.quit()
	print 'tearDownModule',__name__
	
#@unittest.skip('')
class TestUnits(unittest.TestCase):
	"""Tests the MainWindow"""	
#	@unittest.skip('')
	def test_base(self):
		"""Test conversions between base units"""
		c=units.Converter('celsius','kelvin')
		self.assertEqual(c.from_server(25), 298.15)
		self.assertEqual(c.from_client(298.15), 25)
		
		c=units.Converter('kelvin','celsius')
		self.assertEqual(c.from_server(298.15), 25)
		self.assertEqual(c.from_client(25), 298.15)		
		
	def test_classmethod(self):
		"""Test direct conversion via classmethod"""
		self.assertEqual(units.Converter.convert('celsius','kelvin',25),298.15)
		self.assertEqual(units.Converter.convert('kelvin','celsius',298.15),25)
		
	def test_nonbase(self):
		"""Test conversions between non-base units"""
		c=units.Converter('kelvin','fahrenheit')
		self.assertEqual(c.from_server(298.15),77.0)
		self.assertEqual(c.from_client(77.0),298.15)
		
	def test_der(self):
		"""Check derivative factors for client->server and server->client conversions"""
		c=units.Converter('millimeter','nanometer')
		self.assertEqual(c.csd,1E-6)
		self.assertEqual(c.scd,1E6)
		
		
if __name__ == "__main__":
	unittest.main()  