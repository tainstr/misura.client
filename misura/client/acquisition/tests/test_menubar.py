#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import functools
from misura import utils_testing as ut

from misura.client.acquisition import menubar
from misura import instrument

from test_controls import Parent
from misura import server

from PyQt4 import QtGui,QtCore
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
class MenuBar(unittest.TestCase):
	def setUp(self):
		self.root=server.MainServer()
		self.rem=self.root.instruments[0]
		self.rem.parent=lambda: self.root
		self.rem.server=self.root
		self.parent=Parent()
		self.parent.fixedDoc=False
		self.m=menubar.MenuBar(self.root,self.parent)
	
	def test_init(self):
		n=len(self.root.instruments)
		self.assertEqual(len(self.m.lstInstruments),n)
		# Should add one action per instrument to the instrument menu
		self.assertEqual(len(self.m.instruments.actions()),n)
		
		lst=self.root['instruments']
		print '>>lstInstruments',self.m.lstInstruments
		print '>>instruments',self.m.instruments.actions()
			
#	@unittest.skip('')
	def test_setInstrument(self):
		#FIXME: Need a better faked parent!
		self.m.setInstrument(self.rem,self.root)
		
	def test_updateActions(self):
		self.m.updateActions()
		
		
if __name__ == "__main__":
	unittest.main()  
