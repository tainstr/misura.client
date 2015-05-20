#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests single-file simplified Plot"""
import unittest

import os
from misura.client.tests import iutils_testing as iut
from misura.client.graphics import Plot
from misura.client import filedata
from misura.client.navigator import Navigator
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

nativem4=os.path.join(iut.data_dir,'device_22.h5')
nativem4='/home/daniele/misura/misura/storage/data/hsm/cube2.h5'
class TestPlot(unittest.TestCase):
	def setUp(self):
		self.p=Plot()
		self.nav=Navigator()
		self.nav.connect(self.p,QtCore.SIGNAL('hide_show(QString)'),self.nav.plot)
		
	def test(self):
		doc=filedata.MisuraDocument(nativem4)
		doc.reloadData()
		self.p.set_doc(doc)
		self.nav.set_doc(doc)
		self.p.updateCurvesMenu()
		self.p.updateCurveActions()
		self.p.hide_show('0:hsm/sample0/Vol')
		if __name__=='__main__':
			self.p.show()
			app.exec_()
		
		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
