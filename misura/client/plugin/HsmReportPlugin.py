#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
from ReportPlugin import ReportPlugin
from utils import OperationWrapper
import veusz.plugins as plugins
from report_plugin_utils import wr, render_meta

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
		self.report_plugin = ReportPlugin(self.add_shapes, sample)

	def apply(self, cmd, fields):
		self.report_plugin.apply(cmd, fields, 'report_hsm.vsz', 'Vol')

	@property
	def fields(self):
		return self.report_plugin.fields

	def add_shapes(self, sample, toset, page, dict_toset, smp_path, test, doc):
		msg=''
		for sh in ('Sintering', 'Softening','Sphere','HalfSphere','Melting'):
			if not sample.has_key(sh):
				return

		for sh in ('Sintering', 'Softening','Sphere','HalfSphere','Melting'):
			pt=sample[sh]
			if pt['time'] in ['None',None,'']:
				msg+='None\\\\'
				continue
			cf={'dataset':smp_path+'/profile',
				'filename':test.params.filename,
 				'target':pt['time']-zt}
			dict_toset(page.getChild(sh),cf)
			T='{}{{\\deg}}C'.format(int(pt['temp']))
			toset(page.getChild('lbl_'+sh),'label',sh+', '+T)
			msg+=T+'\\\\'
		toset(page.getChild('shapes'),'label',msg)
		
		dict_toset(page.getChild('initial'),{'dataset':smp_path+'/profile',
 				'filename':test.params.filename,'target':0})
		T=doc.data[test.prefix+'kiln/T'].data[0]
		toset(page.getChild('lbl_initial'),'label','Initial, {}{{\\deg}}C'.format(int(T)))

		toset(page.getChild('standard'),'label',wr('Standard',sample['preset'],50))


plugins.toolspluginregistry.append(HsmReportPlugin)