#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Test for thermal cycle editor"""
import unittest
from misura.canon.logger import Log as logging
from misura import utils_testing as ut
from misura.client.graphics import thermal_cycle
from misura import kiln
from PyQt4 import QtGui,QtCore
from PyQt4.QtTest import QTest

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	ut.parallel(0)

def tearDownModule():
	logging.debug('%s', 'Quitting app')
	logging.debug('%s %s', 'tearDownModule', __name__)
	
	
class Designer(unittest.TestCase):
	
	def test(self):
		k=kiln.Kiln()
		k._writeLevel=5
		k._readLevel=5
		call=lambda f, *ar,**kw: getattr(k, f)(*ar, **kw)
		setattr(k, 'call', call)
		tcd=thermal_cycle.ThermalCycleDesigner(k)
		if __name__=='__main__':
			tcd.show()
			QtGui.qApp.exec_()
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
	
