#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests aTable widget."""
import unittest
from misura.canon.logger import Log as logging
from misura import utils_testing as ut
from misura.client import widgets
from misura.device import Node 
from misura.canon import option
from PyQt4 import QtGui,QtCore
logging.debug('%s %s', 'Importing', __name__)
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	ut.parallel(0)

def tearDownModule():
	logging.debug('%s', 'Quitting app')
	logging.debug('%s %s', 'tearDownModule', __name__)
	
class aTable(unittest.TestCase):
	def setUp(self):
		self.root=Node()
		
	def wgGen(self):
		self.assertTrue(self.root.has_key('test'))
		w=widgets.build(self.root, self.root, self.root.gete('test'))
		# The current value is not initialized (gete() returns {current:None} )
		self.assertTrue(w is not False)
		return w
		
	def test(self):
		self.root.sete('test', option.ao({}, 'test', 'Table',[[('ColStr','String'),('ColInt','Integer'),('ColFloat','Float')],['pippo',1,0.5]])['test'])
		w=self.wgGen()
		if __name__=='__main__':
			w.show()
			QtGui.qApp.exec_()
			
if __name__ == "__main__":
	unittest.main(verbosity=2)  
	
	
