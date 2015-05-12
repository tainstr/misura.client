#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Get calibration factor from standard expansion curve"""
from copy import copy
import numpy as np

import veusz.widgets
import veusz.plugins as plugins
import veusz.document as document
import utils 
from misura.client import _, units

from misura.canon.csutil import find_nearest_val

# name: (T, %dL/L20°C)
standards={
	'NIST SRM738':(	np.array([  20,  27,  67, 107, 147, 187, 227, 267, 307, 347, 387, 427, 467, 507]),
					np.array([   0,  69, 466, 872,1288,1714,2149,2593,3048,3511,3984,4467,4959,5461])*10**-4),
}

class CalibrationFactorPlugin(utils.OperationWrapper,plugins.ToolsPlugin):
	"""Dilatometry calibration factor calculation"""
	# a tuple of strings building up menu to place plugin on
	menu = ('Misura',_('Calibration factor'))
	# unique name for plugin
	name = 'Calibration Factor'
	# name to appear on status tool bar
	description_short = _('Dilatometry calibration factor')
	# text to appear in dialog box
	description_full = _('Get calibration factor from standard expansion curve')
	preserve=True
	
	def __init__(self,d='',T='',std='NIST SRM738',start=50,end=50,label=True,add=True):
		"""Make list of fields."""
		
		self.fields = [ 
			plugins.FieldDataset("d", descr=_("Expansion dataset"),default=d),
			plugins.FieldDataset("T", descr=_("Temperature dataset"),default=T),
			plugins.FieldCombo("std",descr=_("Calibraiton Standard"),items=['NIST SRM738'],default=std),
			plugins.FieldFloat('start', descr=_('First temperature margin'), default=start),
			plugins.FieldFloat('end', descr=_('Last temperature margin'), default=end),
			plugins.FieldBool('label', 'Draw calibration label', default=label),
			plugins.FieldBool('add', 'Add calibraiton datasets', default=add),
		]
	
	def apply(self, cmd, fields):
		"""Do the work of the plugin.
		cmd: veusz command line interface object (exporting commands)
		fields: dict mapping field names to values
		"""
		self.ops=[]
		self.doc=cmd.document
		
		ds=self.doc.data[fields['d']]
		Ts=self.doc.data[fields['T']]
		# Convert to percentile, if possible
		if not getattr(ds,'m_percent',False):
			if getattr(ds,'m_initialDimension',False):
				ds=units.percentile_conversion(ds,'To Percent', auto=False)
		T=Ts.data
		# Cut away any cooling
		while max(T)!=T[-1]:
			i=np.where(T==max(T))[0]
			T=T[:i]
		d=ds.data[:len(T)]
		
		# Standard
		sT,sd=standards[fields['std']]
		(s_slope,s_const),s_res,s_rank,s_sing,s_rcond=np.polyfit(sT,sd,1,full=True)
		self.s_slope,self.s_const=s_slope,s_const
		print 'Standard',s_slope,s_const,s_res
		# Find start/end T
		start=max(sT[0],T[0])+fields['start']
		end=min(sT[-1],T[-1])-fields['end']
		print 'T start,end',start,end
		# Cut datasets
		si=find_nearest_val(T,start,get=T.__getitem__)
		ei=find_nearest_val(T,end,get=T.__getitem__)
		print 'Cutting',si,ei
		T=T[si:ei]
		d=d[si:ei]
		(slope,const),res,rank,sing,rcond=np.polyfit(T,d,1,full=True)
		res=res[0]/np.sqrt(len(T))
		# Convert from percentage to micron
		um=res*ds.m_initialDimension/100
		print 'Sample',slope,const,res,um,ds.m_initialDimension
		factor=s_slope/slope
		micron=u'\u03bcm'
		msg=_('Calibration factor: {} \nStandard deviation: \n    {} %\n    {} {}').format(factor,res,um,micron)
		print msg
		self.msg=msg
		self.slope,self.const=slope,const
		self.fld,self.ds,self.T,self.d,self.sT,self.sd=fields,ds,T,d,sT,sd
		self.factor,self.res,self.um=factor,res,um
		if fields['label']:
			self.label()
		if fields['add']:
			self.add_datasets()
		self.apply_ops()
		return factor,res
	
	def add_datasets(self):
		"""Add standard and fitted datasets for further evaluations (plotting, etc)"""
		# Adding plot data
		fields=self.fld
		name=fields['std'].replace(' ','_')
		p=fields['d']+'_'+name
		# Evaluate std fit over regular T
		T=self.doc.data[fields['T']].data
		f=np.poly1d((self.s_slope,self.s_const))
		d=f(T)
		dsd=copy(self.ds)
		dsd.data=plugins.numpyCopyOrNone(d)
		dsd.m_var=name
		dsd.m_pos=1
		dsd.m_name=name
		dsd.m_col=name
		dsd.m_percent=True
		self.ops.append(
				document.OperationDatasetSet(p,dsd))
		
		# Fitting
		f=np.poly1d((self.slope,self.const))
		df=f(T)
		dsf=copy(self.ds)
		dsf.data=plugins.numpyCopyOrNone(df)
		dsf.m_var=name+'_fit'
		dsf.m_pos=2
		dsf.m_name=dsf.m_var
		dsf.m_col=dsf.m_var
		dsd.m_percent=True
		self.ops.append(
				document.OperationDatasetSet(p+'_fit',dsf))
		
	def label(self):
		"""Draw label"""
		cur = self.fld.get('currentwidget')
		g=self.doc.resolveFullWidgetPath(cur)
		g=utils.searchFirstOccurrence(g,['graph','page'])
		if g is None or g.typename not in ['graph','page']:
			raise plugins.ToolsPluginException('Impossible to draw the label. Select a page or a graph.')
		name='lbl_'+self.fld['d'].replace('summary/','').replace('/','_')
		if not g.getChild(name):			
			self.ops.append(document.OperationWidgetAdd(g,'label',name=name))
			self.apply_ops(self.name+':CreateLabel')
		lbl=g.getChild(name)
		self.toset(lbl,'label',self.msg.replace('\n','\\\\'))
		
		
		
plugins.toolspluginregistry.append(CalibrationFactorPlugin)

