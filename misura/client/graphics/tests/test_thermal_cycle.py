#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Test for thermal cycle editor"""
import unittest
from misura import utils_testing as ut
from misura.client.graphics import thermal_cycle
from misura import kiln
from PyQt4 import QtGui,QtCore
from PyQt4.QtTest import QTest
app=False
print 'Importing',__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])
	ut.parallel(0)

def tearDownModule():
	global app
	print 'Quitting app'
	app.quit()
	print 'tearDownModule',__name__
	
	
class Designer(unittest.TestCase):
	
	def test(self):
		k=kiln.Kiln()
		call=lambda f, *ar,**kw: getattr(k, f)(*ar, **kw)
		setattr(k, 'call', call)
		tcd=thermal_cycle.ThermalCycleDesigner(k)
		if __name__=='__main__':
			tcd.show()
			app.exec_()
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
	
