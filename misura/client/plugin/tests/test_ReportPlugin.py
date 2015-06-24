#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the ShapesPlugin."""
import unittest
import os
import veusz.document as document
from misura.client import filedata, iutils
from misura.client.tests import iutils_testing
from misura.client import plugin
from PyQt4 import QtGui



class ReportPlugin(unittest.TestCase):
	"""Tests the CalibrationPlugin"""	

	def do(self,doc,target):
		fields={'sample':target}
		p=plugin.ReportPlugin()
		p.apply(self.cmd,fields)
			
	def test_hsm(self):
		"""Double import a file and subtract the same datasets."""
		# Simulate an import
		nativem4 = os.path.join(iutils_testing.data_dir,'test_video.h5')
		imp = filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc = filedata.MisuraDocument()
		self.cmd=document.CommandInterface(doc)
		plugin.makeDefaultDoc(self.cmd)
		imp.do(doc)
		# Import again
		imp.do(doc)
		doc.model.refresh()
		tree=doc.model.tree
		entry=tree.traverse('0:hsm/sample0')
		self.assertTrue(entry!=False)
		self.do(doc,entry)
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
