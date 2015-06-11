#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests role selector widget."""
import unittest
import functools
import logging
from time import time
from misura import utils_testing as ut
from misura.client import widgets
from misura.device import Node 
from misura.canon import option
from PyQt4 import QtGui,QtCore
from PyQt4.QtTest import QTest

app=False
logging.debug('%s %s', 'Importing', __name__)
main=__name__=='__main__'

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	global app
	app=QtGui.QApplication([])
	ut.parallel(0)

def tearDownModule():
	global app
	logging.debug('%s', 'Quitting app')
	app.quit()
	logging.debug('%s %s', 'tearDownModule', __name__)

	
class aTime(unittest.TestCase):
	shift=5
	"""Client-server time shift"""
	tol=0.001
	"""Test comparison tolerance (seconds)"""
	def setUp(self):
		self.root=Node()
		self.root.time=lambda: time()-self.shift
		
	def wgGen(self,k='val'):
		self.assertTrue(self.root.has_key(k))
		logging.debug('%s', self.root.gete(k))
		w=widgets.build(self.root, self.root, self.root.gete(k))
		# The current value is not initialized (gete() returns {current:None} )
		self.assertTrue(w is not False)
		return w
		
		
	def test(self):
		self.root.sete('val', option.ao({}, 'val', 'Time')['val'])
		w=self.wgGen()
		self.assertAlmostEqual(w.delta,self.shift,delta=self.tol)
		# Server-side update
		t=time()+60
		self.root['val']=t
		w.get()
		self.assertAlmostEqual(w.current,t,delta=self.tol)
		self.assertAlmostEqual(self.root['val'],t,delta=self.tol)
		g=w.twg.dateTime().toMSecsSinceEpoch()/1000.
		self.assertAlmostEqual(g,t+self.shift,delta=self.tol)
		# User editing
		t=time()+120
		qdt=QtCore.QDateTime()
		qdt.setMSecsSinceEpoch(t*1000)
		w.edited(qdt)
		self.assertAlmostEqual(w.current,t-self.shift,delta=self.tol)
		self.assertAlmostEqual(self.root['val'],t-self.shift,delta=self.tol)
		

class aDelay(aTime):
	def test_human(self):
		self.root.sete('delay', option.ao({}, 'delay', 'Time')['delay'])
		self.root.sete('delayStart', option.ao({}, 'delayStart', 'Boolean')['delayStart'])
		w=self.wgGen('delay')
		w1=widgets.build(self.root, self.root, self.root.gete('delayStart'))
		w.lay.addWidget(w1)
		if main:
			w.show()
			QtGui.qApp.exec_()
	
			
if __name__ == "__main__":
	unittest.main(verbosity=2)  
