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
			
	def test_hsm(self):
		"""Create HSM report"""
		self.verify_plugin('test_video.h5', '0:hsm/sample0', 'report_hsm.vsz', 'Vol')

	def test_horizontal(self):
		"""Create Horizontal Dilatometer report"""
		self.verify_plugin('test_horizontal.h5', '0:horizontal/sample0', 'report_horizontal.vsz', 'd')

	def test_vertical(self):
		"""Create Vertical Dilatometer report"""
		self.verify_plugin('test_vertical.h5', '0:vertical/sample0', 'report_vertical.vsz', 'd')

	def test_flex(self):
		"""Create Flex report"""
		self.verify_plugin('test_flex.h5', '0:flex/sample0', 'report_flex.vsz', 'd')


	def verify_plugin(self, test_data_file, entry_path, template_file_name, measure_to_plot):
		nativem4 = os.path.join(iutils_testing.data_dir, test_data_file)
		imp = filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
		doc = filedata.MisuraDocument()
		self.cmd=document.CommandInterface(doc)
		plugin.makeDefaultDoc(self.cmd)
		imp.do(doc)
		imp.do(doc)
		doc.model.refresh()
		tree=doc.model.tree
		entry=tree.traverse(entry_path)

		self.assertTrue(entry!=False)
		fields = {'sample': entry, 'measure_to_plot': measure_to_plot, 'template_file_name': template_file_name}
		plugin.ReportPlugin(None, template_file_name, measure_to_plot).apply(self.cmd, fields)

		
		
if __name__ == "__main__":
	unittest.main(verbosity=2)  
