#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Changes measurement unit to a dataset."""
import veusz.plugins as plugins
import numpy as np
from copy import copy
import veusz.document as document
import utils
from .. import units
from misura.client.iutils import get_plotted_tree
from PercentilePlugin import percentile_conversion

def units_conversion(ds,to_unit):
	from_unit=getattr(ds, 'unit',False)
	if not from_unit or to_unit in ['None','',None,False]:
		raise plugins.DatasetPluginException('Selected dataset does not have a measurement unit.') 
	# Implicit To-From percentile conversion 
	from_group=units.known_units[from_unit]
	to_group=units.known_units[to_unit]
	if from_group!=to_group:
		if 'part' not in (from_group,to_group):
			raise plugins.DatasetPluginException('Incompatible conversion: from {} to {}'.format(from_unit,to_unit))
		ds1=percentile_conversion(ds)
		if to_group=='part':
			from_unit='percent'
		elif from_group=='part':
			# Guess default unit for destination dimension
			from_unit=getattr(ds,'old_unit',units.user_defaults[to_group])
	else:
		# No implicit percentile conversion
		ds1=copy(ds)
			
	out=units.Converter.convert(from_unit,to_unit,np.array(ds1.data))
	ini=getattr(ds,'m_initialDimension',0)
	old_unit=getattr(ds,'old_unit',from_unit)
	old_group=units.known_units[old_unit]
	if ini and (old_group==to_group==from_group) and 'part'!=to_group:
		ini1=units.Converter.convert(from_unit,to_unit,ini)
		ds.m_initialDimension=ini1
		ds1.m_initialDimension=ini1
		print 'converting m_initialDimension',ini,ini1
	ds1.data=plugins.numpyCopyOrNone(out)
	ds1.unit=to_unit
	return ds1

class UnitsConverterTool(utils.OperationWrapper,plugins.ToolsPlugin):
	"""Convert between measurement units"""
	# tuple of strings to build position on menu
	menu = ('Misura', 'Change Unit')
	# internal name for reusing plugin later
	name = 'Units Converter'
	# string which appears in status bar
	description_short = 'Convert between measurement units'

	# string goes in dialog box
	description_full = ('Convert dataset to different measurement unit')

	def __init__(self, ds='',propagate=False,convert='None'):
		"""Define input fields for plugin."""
		
		kgroup,f,p=units.get_unit_info(convert,units.from_base)
		items=units.from_base.get(kgroup,{convert:lambda v: v}).keys()
		self.fields = [
			plugins.FieldDataset('ds', 'Dataset to convert', default=ds),
			plugins.FieldCombo("convert", descr="Convert to:", items=items, default=convert),
			plugins.FieldBool("propagate", descr="Apply to all datasets sharing the same Y axis:", default=propagate),
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

		ds1=units_conversion(ds,fields['convert'])
		self.ops.append(document.OperationDatasetSet(fields['ds'],ds1))
		self.apply_ops()
		
		####
		# PROPAGATION
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
		# Create a non-propagating unit conversion operation for each dataset found
		for nds in cvt:
			if nds==fields['ds']:
				continue
			ncur=getattr(self.doc.data[nds],'unit',False)
			if not ncur:
				continue
			print 'Really propagating unit conversion to',nds
			fields={'ds': nds, 'propagate':False,'convert':fields['convert']}
			self.ops.append(document.OperationToolsPlugin(UnitsConverterTool(),fields))
		# Update axis labels
		old=units.symbols.get(ds.unit,False)
		new=units.symbols.get(fields['convert'],False)
		if old and new:
			for ax in upax:
				ax=self.doc.resolveFullWidgetPath(ax)
				lbl=ax.settings.label.replace(old,new)
				self.toset(ax,'label', lbl)
				
		# Apply everything
		self.apply_ops('UnitsConverterTool: Propagate')
		
		
		
plugins.toolspluginregistry.append(UnitsConverterTool)
