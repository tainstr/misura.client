#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import veusz.plugins as plugins
import numpy
import scipy
import veusz.document as document

from FieldMisuraNavigator import FieldMisuraNavigator

class MotorCorrectionPlugin(plugins.ToolsPlugin):
	"""Correct motor movements in Misura3 flex/odlt/odht tests"""
	# a tuple of strings building up menu to place plugin on
	menu = ('Misura3','Correct motor movements')
	# unique name for plugin
	name = 'MotorCorrection'
	# name to appear on status tool bar
	description_short = 'Correct motor movements'
	# text to appear in dialog box
	description_full = 'Correct motor movements extrapolating moving rate before and after the intervention'
	
	def __init__(self):
		"""Make list of fields."""
		self.fields = [ 
			FieldMisuraNavigator("sample", descr="Target sample:", depth='sample'),
		]

	def apply(self, interface, fields):
		"""Do the work of the plugin.
		interface: veusz command line interface object (exporting commands)
		fields: dict mapping field names to values
		"""
		smp=fields['sample']
		#FIXME: DEPRECATED
		from misura.client import filedata
		if not filedata.ism(smp, filedata.Sample):
			t=str(type(smp))
			raise plugins.ToolsPluginException('The target must be a sample, found: '+t)
		if filedata.ism(smp.linked, filedata.LinkedMisuraFile):
			raise plugins.ToolsPluginException('misura tests cannot be corrected, as motor movement correction is performed runtime.')
		pass
plugins.toolspluginregistry.append(MotorCorrectionPlugin)

