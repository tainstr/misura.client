#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Zoom by changing axes scales."""
import veusz.plugins as plugins
import veusz.document as document
import utils
class ZoomAxesPlugin(utils.OperationWrapper,plugins.ToolsPlugin):
	"""Re-scale all axes in order to zoom in/out from the graph"""
	# a tuple of strings building up menu to place plugin on
	menu = ('General','Zoom axes')
	# unique name for plugin
	name = 'Zoom by axes'
	# name to appear on status tool bar
	description_short = 'Zoom by rescaling axes'
	# text to appear in dialog box
	description_full = 'Re-scale axes in order to zoom in/out from the graph.'
	
	def __init__(self):
		"""Make list of fields."""
		
		self.fields = [ 
			plugins.FieldFloat("zoom", descr="Zoom factor (%). \n>0: zoom in. \n<0: zoom out. \n=0: restores autoranges.", default=-10,minval=-300,maxval=300),
			plugins.FieldBool("x", descr="Scale also horizontal (X) axes", default=False),
		]

	
	def apply(self, cmd, fields):
		"""Do the work of the plugin.
		cmd: veusz command line interface object (exporting commands)
		fields: dict mapping field names to values
		"""
		self.ops=[]
		doc=cmd.document
		self.doc=doc
		g=doc.resolveFullWidgetPath(fields['currentwidget'])
		g=utils.searchFirstOccurrence(g,'graph')
		if g is None: 
			raise plugins.ToolsPluginException('You should use this tool on a graph object.')
		z=-fields['zoom']
		x=fields['x']
		# Apply zoom on all axes:
		for ax in g.children:
			if ax.typename not in ('axis','axis-function'): 
				continue
			if not x and ax.settings.direction=='horizontal': 
				continue
			if z==0:
				self.toset(ax,'min','Auto')
				self.toset(ax,'max','Auto')
				continue		
			m,M=ax.plottedrange
			# Delta
			d=z*(M-m)/200.
			self.toset(ax,'min',float(m-d))
			self.toset(ax,'max',float(M+d))
			
		self.apply_ops('ZoomAxes %.1f%%' % z)		


plugins.toolspluginregistry.append(ZoomAxesPlugin)