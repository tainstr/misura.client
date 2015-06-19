#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Test for thermal cycle editor"""
import unittest
from misura.client.tests import iutils_testing
from misura.client.graphics import thermal_cycle
from misura import kiln
from PyQt4 import QtGui,QtCore

	
class Designer(unittest.TestCase):
	@unittest.skipIf(__name__ != '__main__', "should be executed only manually")
	def test(self):
		k=kiln.Kiln()
		k._writeLevel=5
		k._readLevel=5
		call=lambda f, *ar,**kw: getattr(k, f)(*ar, **kw)
		setattr(k, 'call', call)
		tcd=thermal_cycle.ThermalCycleDesigner(k)
		tcd.show()
		QtGui.qApp.exec_()
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)
