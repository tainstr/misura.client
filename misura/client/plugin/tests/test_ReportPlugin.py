#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the ShapesPlugin."""
import unittest
import os
import veusz.document as document

from misura.client.tests import iutils_testing
from misura.client import filedata
from misura.client import plugin



class ReportPlugins(unittest.TestCase):
	"""Tests the CalibrationPlugin"""	

	def do(self, doc, target, plugin_to_apply):
		fields={'sample':target}
		plugin_to_apply().apply(self.cmd,fields)
			
	def test_hsm(self):
		"""Create HSM report"""
		# Simulate an import
		nativem4 = os.path.join(iutils_testing.data_dir,'test_video.h5')
		imp = filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc = filedata.MisuraDocument()
		self.cmd=document.CommandInterface(doc)
		plugin.makeDefaultDoc(self.cmd)
		imp.do(doc)
		imp.do(doc)
		doc.model.refresh()
		tree=doc.model.tree
		entry=tree.traverse('0:hsm/sample0')

		self.assertTrue(entry!=False)
		self.do(doc, entry, plugin.HsmReportPlugin)


	def test_horizontal(self):
		"""Create Horizontal Dilatometer report"""
		# Simulate an import
		nativem4 = os.path.join(iutils_testing.data_dir,'test_horizontal.h5')
		imp = filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc = filedata.MisuraDocument()
		self.cmd=document.CommandInterface(doc)
		plugin.makeDefaultDoc(self.cmd)
		imp.do(doc)
		doc.model.refresh()
		tree=doc.model.tree
		entry=tree.traverse('0:horizontal/sample0')

		self.assertTrue(entry!=False)
		self.do(doc, entry, plugin.HorizontalReportPlugin)

	def test_vertical(self):
		"""Create Vertical Dilatometer report"""
		# Simulate an import
		nativem4 = os.path.join(iutils_testing.data_dir,'test_vertical.h5')
		imp = filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc = filedata.MisuraDocument()
		self.cmd=document.CommandInterface(doc)
		plugin.makeDefaultDoc(self.cmd)
		imp.do(doc)
		doc.model.refresh()
		tree=doc.model.tree
		entry=tree.traverse('0:vertical/sample0')

		self.assertTrue(entry!=False)
		self.do(doc, entry, plugin.VerticalReportPlugin)

	def test_flex(self):
		"""Create Flex report"""
		# Simulate an import
		nativem4 = os.path.join(iutils_testing.data_dir,'test_flex.h5')
		imp = filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc = filedata.MisuraDocument()
		self.cmd=document.CommandInterface(doc)
		plugin.makeDefaultDoc(self.cmd)
		imp.do(doc)
		doc.model.refresh()
		tree=doc.model.tree
		entry=tree.traverse('0:flex/sample0')

		self.assertTrue(entry!=False)
		self.do(doc, entry, plugin.FlexReportPlugin)
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
