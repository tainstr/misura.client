#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the ShapesPlugin."""
import unittest
import os
import veusz.document as document
from misura.client import filedata, iutils
from misura.client.tests import iutils_testing as iut
from misura.client import plugin
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

nativem4=os.path.join(iut.data_dir,'hsm_test.h5')
nativem4='/home/daniele/f3x3.h5'

class ReportPlugin(unittest.TestCase):
	"""Tests the CalibrationPlugin"""	

	def do(self,doc,target):
		fields={'sample':target}
		p=plugin.ReportPlugin()
		p.apply(self.cmd,fields)
			
	def test(self):
		"""Double import a file and subtract the same datasets."""
		# Simulate an import
		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc=filedata.MisuraDocument()
		self.cmd=document.CommandInterface(doc)
		imp.do(doc)
		# Import again
		imp.do(doc)
		print doc.data.keys()
		doc.model.refresh()
		tree=doc.model.tree
		print 'tree child',tree.get('').children
		entry=tree.traverse('hsm/sample0')
		self.assertTrue(entry!=False)
		print 'found entry',entry
		self.do(doc,entry)
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
