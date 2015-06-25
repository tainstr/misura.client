#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
from ReportPlugin import ReportPlugin
from utils import OperationWrapper
import veusz.plugins as plugins

class HsmReportPlugin(OperationWrapper, plugins.ToolsPlugin):
	# a tuple of strings building up menu to place plugin on
	menu = ('Misura','Report')
	# unique name for plugin
	name = 'Report'
	# name to appear on status tool bar
	description_short = 'Create Report'
	# text to appear in dialog box
	description_full = 'Create Report on new page'

	def __init__(self, sample = None):
		self.report_plugin = ReportPlugin(sample)

	def apply(self, cmd, fields):
		self.report_plugin.apply(cmd, fields, 'report_hsm.vsz', 'Vol')

	@property
	def fields(self):
		return self.report_plugin.fields
