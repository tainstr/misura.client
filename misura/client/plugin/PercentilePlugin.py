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
from misura.client.iutils import get_plotted_tree
from .. import units

def percentile_conversion(ds,action='Invert',auto=True):
	cur=getattr(ds, 'm_percent',False)
	# invert action
	if action=='Invert':
		if cur: action='To Absolute'
		else: action='To Percent'
		print 'percentile_conversion doing',action,cur
		
	ini=getattr(ds, 'm_initialDimension',False)
	out=numpy.array(ds.data)
	# Auto initial dimension
	if not ini:
		if not auto or action!='To Percent':
			raise plugins.DatasetPluginException('Selected dataset does not have an initial dimension set. \
		Please first run "Initial dimension..." tool.')
		ds.m_initialDimension=out[:5].mean()
		
	# Evaluate if the conversion is needed 
	# based on the current status and the action requested by the user
	if action=='To Absolute':
		out=out*ds.m_initialDimension/100.
		ds.m_percent=False
		u=getattr(ds,'unit','percent')
		# If current dataset unit is not percent, convert to
		out=units.Converter.convert(u,'percent',out)	
		ds.unit=getattr(ds,'old_unit',False)
		ds.old_unit=u
	elif action=='To Percent':
		out=100.*out/ds.m_initialDimension
		ds.m_percent=True
		ds.old_unit=ds.unit
		ds.unit='percent'
	ds1=copy(ds)
	ds1.data=plugins.numpyCopyOrNone(out)
	return ds1
	
	
class PercentilePlugin(utils.OperationWrapper,plugins.ToolsPlugin):
	"""Convert to percentile value"""
	# tuple of strings to build position on menu
	menu = ('Misura', 'Percentile')
	# internal name for reusing plugin later
	name = 'Percentile'
	# string which appears in status bar
	description_short = 'Convert to/from percentile values'

	# string goes in dialog box
	description_full = ('Convert to percentile values, given an initial dimension')

	def __init__(self, ds='',propagate=False,action='Invert',auto=True):
		"""Define input fields for plugin."""
		self.fields = [
			plugins.FieldDataset('ds', 'Dataset to convert', default=ds),
			plugins.FieldBool("propagate", descr="Apply to all datasets sharing the same Y axis:", default=propagate),
			plugins.FieldCombo("action", descr="Conversion mode:", items=['Invert','To Percent','To Absolute'], default=action),
			plugins.FieldBool("auto", descr="Auto initial dimension", default=True)
		]
		
	

	def apply(self, interface, fields):
		"""Do the work of the plugin.
		interface: veusz command line interface object (exporting commands)
		fields: dict mapping field names to values
		"""
		self.ops=[]
		self.doc=interface.document
		# raise DatasetPluginException if there are errors
		ds=interface.document.data.get(fields['ds'], False)
		if not ds:
			raise plugins.DatasetPluginException('Dataset not found'+fields['ds'])
		
		ds1=percentile_conversion(ds,fields['action'],fields['auto'])
		
		self.ops.append(document.OperationDatasetSet(fields['ds'],ds1))
		self.apply_ops()
		print 'Converted %s %s using initial dimension %.2f.' % (fields['ds'], fields['action'], ds.m_initialDimension)
# 		QtGui.QMessageBox.information(None,'Percentile output',
# 				'Converted %s %s using initial dimension %.2f.' % (fields['ds'], msg, ds.m_initialDimension))		
		if not fields['propagate']: return
		# Find all datasets plotted with the same Y axis
		cvt=[]
		tree=get_plotted_tree(self.doc.basewidget)
		upax=[]
		for axp, dslist in tree['axis'].iteritems():
			if not fields['ds'] in dslist:
				continue
			print 'Propagating to',cvt
			cvt+=dslist
			upax.append(axp)
		cvt=list(set(cvt))
		if fields['ds'] in cvt:
			cvt.remove(fields['ds'])
		act='To Percent' if ds.m_percent else 'To Absolute'
		# Create a non-propagating percentile operation for each dataset found
		for nds in cvt:
			ncur=getattr(self.doc.data[nds],'m_percent',None)
			if ncur==ds.m_percent:
				continue
			print 'Really propagating percentile to',nds
			fields={'ds': nds, 'propagate':False,'action':act,'auto':True}
			self.ops.append(document.OperationToolsPlugin(PercentilePlugin(),fields))
		# Update axis labels
		old=units.symbols.get(ds.old_unit,False)
		new=units.symbols.get(ds.unit,False)
		if old and new:
			for ax in upax:
				ax=self.doc.resolveFullWidgetPath(ax)
				lbl=ax.settings.label.replace(old,new)
				self.toset(ax,'label', lbl)
		# Apply everything
		self.apply_ops('Percentile: Propagate')
		
		
		
plugins.toolspluginregistry.append(PercentilePlugin)
