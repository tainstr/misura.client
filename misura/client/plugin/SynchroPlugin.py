#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Synchronize two curves."""
import veusz.plugins as plugins
import veusz.document as document
import numpy as np
from PyQt4 import QtGui, QtCore
import copy
import utils

class SynchroPlugin(utils.OperationWrapper,plugins.ToolsPlugin):
	"""Translate curves so that they equal a reference curve at a known x-point"""
	# a tuple of strings building up menu to place plugin on
	menu = ('Misura','Synchronize two curves')
	# unique name for plugin
	name = 'Synchro'
	# name to appear on status tool bar
	description_short = 'Synchronize'
	# text to appear in dialog box
	description_full = 'Synchronize two or more curves so they equals to a reference curve at the requested x-point.'
	
	def __init__(self):
		"""Make list of fields."""
		
		self.fields = [ 
			plugins.FieldWidget("ref", descr="Reference curve:", widgettypes=set(['xy'])),
			plugins.FieldWidget("trans", descr="Translating curve:", widgettypes=set(['xy'])),
			plugins.FieldFloat("x", descr="Matching X Value",default=0.),
#			plugins.FieldDatasetMulti('dslist','')
			plugins.FieldCombo("mode",descr="Translation Mode:",items=['Translate Values','Translate Axes'],default="Translate Axes")
		]

	def apply(self, cmd, fields):
		"""Do the work of the plugin.
		cmd: veusz command line interface object (exporting commands)
		fields: dict mapping field names to values
		"""
		self.ops=[]
		doc=cmd.document
		self.doc=doc
		ref=doc.resolveFullWidgetPath(fields['ref'])
		trans=doc.resolveFullWidgetPath(fields['trans'])
		if ref.parent!=trans.parent:
			raise plugins.ToolsPluginException('The selected curves must belong to the same graph.')
		if ref.settings.yAxis!=trans.settings.yAxis or ref.settings.xAxis!=trans.settings.xAxis:
			raise plugins.ToolsPluginException('The selected curves must share the same x, y axes.')
		
		# TODO: selezionare l'asse anziché due curve. 
		# Altrimenti, altre curve riferentesi all'asse originario verrebbero sfalsate quando le sue dimensioni si aggiornano!
		
		xax=ref.parent.getChild(ref.settings.xAxis)
		yax=ref.parent.getChild(ref.settings.yAxis)
		
		# X Arrays
		xref=doc.data[ref.settings.xData].data
		xtr=doc.data[trans.settings.xData].data
		
		# Y Arrays
		yref=doc.data[ref.settings.yData].data
		# Keep Y Dataset for translation update
		yds=doc.data[trans.settings.yData]	
		ytr=yds.data
		
		#Search the nearest X value on ref X-array
		dst=np.abs(xref-fields['x'])
		i=np.where(dst==dst.min())[0][0]
		# Get the corresponding Y value on the ref Y-array
		yval_ref=yref[i]
		#Search the nearest X value on trans X-array
		dst=np.abs(xtr-fields['x'])
		i=np.where(dst==dst.min())[0][0]
		# Get the corresponding Y value on the trans Y-array
		yval_tr=ytr[i]
		
		#Delta
		d=yval_tr-yval_ref
		
		msg='curve' if fields['mode']=='Translation Mode' else 'Y axis'
		QtGui.QMessageBox.information(None,'Synchronization Output','Translating the %s by %E.' % (msg,d))
		
		if fields['mode']=='Translate Values':
			new=yds.data-d
			# Create a copy of the dataset
			ydsn=copy.copy(yds)	
			# Change copy's values
			ydsn.data=new
			# Set original dataset to copied one
			op=document.OperationDatasetSet(yds.name(),ydsn)
			doc.applyOperation(op) 
			return True
		
		# Create a new Y axis
		ypath=cmd.CloneWidget(yax.path,trans.parent.path,newname='Trans_'+yax.name)
		trax=doc.resolveFullWidgetPath(ypath)
		self.toset(trax,'label','Trans: '+yax.settings.label)
		self.toset(trax,'Line/transparency',30)
		self.toset(trax,'MajorTicks/transparency',30)
		self.toset(trax,'MinorTicks/transparency',30)
		self.toset(trax,'Label/italic',True)
		
		newmax,newmin=yax.getPlottedRange()
		# Remove Auto ranges from reference axis
		self.toset(yax,'max',float(newmax))
		self.toset(yax,'min',float(newmin))
		self.toset(trax,'max',float(newmax+d))
		self.toset(trax,'min',float(newmin+d))		
		self.toset(trans,'yAxis',trax.name)
		
		self.apply_ops()
		return True

		
				
				


plugins.toolspluginregistry.append(SynchroPlugin)