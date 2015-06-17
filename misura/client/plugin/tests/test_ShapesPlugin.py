#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the ShapesPlugin."""
import unittest
import os
from misura.canon.logger import Log as logging
import veusz.document as document
import veusz.plugins
from misura.client import filedata
from misura.client.tests import iutils_testing as iut
from misura.client import plugin
from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)

def tearDownModule():
	logging.debug('%s %s', 'tearDownModule', __name__)

nativem4=os.path.join(iut.data_dir,'hsm_test.h5')
nativem4='/home/daniele/f3x3.h5'

class ShapesPlugin(unittest.TestCase):
	"""Tests the CalibrationPlugin"""	

	def do(self,doc,target):
		fields={'sample':target,'temp':True,'time':True,'text':'$shape$\\\\%(xlabel)s=%(x)i'}
		p=plugin.ShapesPlugin()
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
		logging.debug('%s', doc.data.keys())
		doc.model.refresh()
		tree=doc.model.tree
		logging.debug('%s %s', 'tree child', tree.get('').children)
		entry=tree.traverse('hsm/sample0/h')
		self.assertTrue(entry!=False)
		logging.debug('%s %s', 'found entry', entry)
		self.do(doc,entry)
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
