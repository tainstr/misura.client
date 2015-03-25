#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import veusz.plugins as plugins
from PyQt4 import QtGui, QtCore
import numpy
import scipy
import veusz.document as document
import utils 
from copy import copy

class InitialDimensionPlugin(utils.OperationWrapper,plugins.ToolsPlugin):
	"""Convert to percentile value"""
	# tuple of strings to build position on menu
	menu = ('Misura', 'Initial dimension')
	# internal name for reusing plugin later
	name = 'InitialDimension'
	# string which appears in status bar
	description_short = 'Configure initial dimension'

	# string goes in dialog box
	description_full = ('Configure initial dimension')

	def __init__(self, ds='', ini=100., auto=True, num=20, method='mean', ds_x=''):
		"""Define input fields for plugin."""
		self.fields = [
			plugins.FieldDataset('ds', 'Dataset to configure', default=ds),
			plugins.FieldFloat('ini', 'Initial dimension value', default=ini),
			plugins.FieldBool('auto', 'OR, automatic calculation based of fist points', default=auto),
			plugins.FieldInt('num', 'Number of point to use in auto-calc', default=num),
			plugins.FieldCombo('method', 'Method for auto-calc', default=method, items=('linear-regression', 'mean')),
			plugins.FieldDataset('ds_x', 'X Dataset for linear regression', default=ds_x),
		]

	def apply(self, interface, fields):
		"""Do the work of the plugin.
		interface: veusz command line interface object (exporting commands)
		fields: dict mapping field names to values
		"""
		self.ops=[]
		self.doc=interface.document
		# raise DatasetPluginException if there are errors
		ds=self.doc.data.get(fields['ds'], False)
		if not ds:
			raise plugins.DatasetPluginException('Dataset not found'+fields['ds'])
		out=numpy.array(ds.data)
		# If data was converted to percentile, convert back to real numbers
		percent=getattr(ds, 'm_percent', False)
		if percent:	out=out*ds.m_initialDimension/100.
		# Calculate automatic initial value
		ini=fields['ini']
		n=fields['num']
		if fields['auto']:
			if n>len(out)/2:
				raise plugins.DatasetPluginException('Too many points used for calculation: %i/%i' %(n, len(out)))
			ini=out[:n]
			if fields['method']=='mean':
				ini=ini.mean()
			elif fields['method']=='linear-regression':
				x=interface.document.data.get(fields['ds_x'], False)
				if not x: raise plugins.DatasetPluginException('Dataset not found'+fields['ds_x'])
				x=numpy.array(x.data)
				(slope,const)=scipy.polyfit(x[:n],ini, 1)
				ini=x[0]*slope+const
		# Convert back to percent if needed
		ds1=copy(ds)
		if percent: 
			out=100.*out/ini
			ds1.data=plugins.numpyCopyOrNone(out)
		orig=getattr(ds, 'm_initialDimension', False)
		if orig and orig!=ini:
			repl=QtGui.QMessageBox.warning(None, 'Initial dimension',
										'Changing initial dimension from %.2f to %.2f. Confirm?' % (orig, ini),
										QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel,  
										defaultButton=QtGui.QMessageBox.Ok)
			if repl!=QtGui.QMessageBox.Ok:
				QtGui.QMessageBox.information(None, 'Initial dimension','Change cancelled')
				return
		ds1.m_initialDimension=ini
		self.ops.append(document.OperationDatasetSet(fields['ds'],ds1))
		self.apply_ops()
		QtGui.QMessageBox.information(None,'Initial dimension output','Initial dimension configured to %.2f' % ini)
		

plugins.toolspluginregistry.append(InitialDimensionPlugin)
