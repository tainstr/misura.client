#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Place datapoints on the characteristic shapes."""
import veusz.plugins as plugins
import veusz.document as document

from FieldMisuraNavigator import FieldMisuraNavigator
from InterceptPlugin import InterceptPlugin
import utils

#TODO: Estendere a tutte le opzioni di tipo Meta.
m4shapes=['Sintering', 'Softening', 'Sphere', 'HalfSphere', 'Melting']

class ShapesPlugin(utils.OperationWrapper,plugins.ToolsPlugin):
	"""Show Misura Microscope shapes in graphics"""
	# a tuple of strings building up menu to place plugin on
	menu = ('Misura','Show characteristic shapes')
	# unique name for plugin
	name = 'Shapes'
	# name to appear on status tool bar
	description_short = 'Show characteristic shapes'
	# text to appear in dialog box
	description_full = 'Draw characteristic shapes on temperature and time graphs'
	
	def __init__(self,sample=None,temp=True,time=True,text='$shape$'):
		"""Make list of fields."""
		#\\\\%(xlabel)s=%(x)i
		self.fields = [ 
			FieldMisuraNavigator("sample", descr="Target sample:", depth='sample',default=sample),
			plugins.FieldText('text', 'Label text', default=text)
		]

	def apply(self, cmd, fields):
		"""Do the work of the plugin.
		cmd: veusz command line interface object (exporting commands)
		fields: dict mapping field names to values
		"""
		self.ops=[]
		self.doc=cmd.document
		smpe=fields['sample']
		p=smpe.path
		if '/sample' not in p:
			raise plugins.ToolsPluginException('The target must be a sample or a sample dataset, found: '+p)
		cur = fields['currentwidget']
		g=self.doc.resolveFullWidgetPath(cur)
		g=utils.searchFirstOccurrence(g,'graph')
		if g is None or g.typename!='graph':
			print 'Found graph:',g
			raise plugins.ToolsPluginException('You should run this tool on a graph')
		print 'ShapesPlugin searching',p
		conf=False
		vds=[]
		if smpe.ds:
			conf=getattr(smpe.ds,'m_conf',False)
			vds.append(smpe.ds.name())
		else:
			for k,ent in smpe.children.iteritems():
				conf=getattr(ent.ds,'m_conf',False)
				if not conf: continue
				if len(ent.ds)>0:
					vds.append(ent.ds.name())
		if not conf or len(vds)==0:
			raise plugins.ToolsPluginException('No metadata found for '+p)
		print 'Found datasets',vds
		smpp=smpe.path
		# Detect if a sample dataset was selected and go up one level
		if smpp.split('/')[-2].startswith('sample'):
			smpp=smpe.parent.path
		smpp=smpp.replace('summary','')
		print 'Found sample path',smpp,p
		smp=conf.toPath(smpp)
		print 'config',smp
		for shape,opt in smp.describe().iteritems():
			if opt['type']!='Meta': continue
			txt=str(fields['text']).replace('$shape$',shape)
			pt=opt['current']
			t=pt['time']; T=pt['temp']
			if t in [0,None,'None'] or T in [0,None,'None']: 
				print 'Shape not found:',shape
				continue
			t-=conf['zerotime']
			# Temperature plotting
			basename=smpe.path.replace('/',':')+'_'
			val=T if cur.endswith('temp') else t
			f={'currentwidget':cur,
				'axis':'X',
				'val':val,
				'text': txt,
				'basename':basename+shape,
				'target':vds,
				'search':'None',
				'searchRange':25
				}
			self.ops.append(document.OperationToolsPlugin(InterceptPlugin(),f))
				
		print 'ShapesPlugin ops',self.ops
		self.apply_ops()
				
				


plugins.toolspluginregistry.append(ShapesPlugin)