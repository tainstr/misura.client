#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
import veusz.dialogs
from veusz import document
from PyQt4.QtCore import Qt
from PyQt4 import QtGui, QtCore

import functools
from . import MisuraDocument, ImportParamsMisura, OperationMisuraImport
from entry import DatasetEntry
from .. import clientconf
from proxy import getFileProxy

ism=isinstance

def node(func):
	"""Decorator for functions which should get currentIndex node if no arg is passed"""	
	@functools.wraps(func)
	def node_wrapper(self,*a,**k):
		n=False
		keyword=True
		# Get node from named parameter
		if k.has_key('node'):
			n=k['node']
		# Or from the first unnamed argument
		elif len(a)>=1:
			n=a[0]
			keyword=False
		# If node was not specified, get from currentIndex
		if n is False:
			n=self.model().data(self.currentIndex(), role=Qt.UserRole)
		elif isinstance(n,document.Dataset):
			n=n.name() # convert to path string
		# If node was expressed as/converted to string, get its corresponding tree entry
		if isinstance(n,str) or isinstance(n, unicode):
			print 'traversing node',n
			n=str(n)
			n=self.model().tree.traverse(n)
		
		if keyword:
			k['node']=n
		else:
			a=list(a)
			a[0]=n
			a=tuple(a)
		print '@node with',n,type(n),isinstance(n,unicode)
		return func(self,*a,**k)
	return node_wrapper

def nodes(func):
	"""Decorator for functions which should get a list of currentIndex nodes if no arg is passed"""
	@functools.wraps(func)
	def node_wrapper(self,*a,**k):
		n=[]
		keyword=True
		# Get node from named parameter
		if k.has_key('nodes'):
			n=k['nodes']
		# Or from the first unnamed argument
		elif len(a)>=1:
			n=a[0]
			keyword=False
		# If node was not specified, get from currentIndex
		if not len(n):
			n=[]
			for idx in self.selectedIndexes():
				n0=self.model().data(idx, role=Qt.UserRole)
				n.append(n0)
		if keyword:
			k['nodes']=n
		else:
			a=list(a)
			a[0]=n
			a=tuple(a)
		print '@nodes with',n,type(n),isinstance(n,unicode)
		return func(self,*a,**k)
	return node_wrapper	

class QuickOps(object):
	"""Quick interface for operations on datasets"""
	_mainwindow=False
	@property
	def mainwindow(self):
		if self._mainwindow is False:
			return self
		return self._mainwindow
	
	def refresh(self):
		print 'refreshing model', self.doc
		self.model().refresh(True)	
		
	@node
	def intercept(self,node=False):
		"""Intercept all curves derived/pertaining to the current object"""
		if ism(node,DatasetEntry):
			dslist=[node.path]
		elif hasattr(node,'datasets'):
			#FIXME: needs paths
			dslist=node.children.keys()
		else: dslist=[]
		from misura.client import plugin
		p=plugin.InterceptPlugin(target=dslist,axis='X')
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.InterceptPlugin)
		self.mainwindow.showDialog(d)

	###
	# File actions
	###
	@node
	def viewFile(self,node=False):
		if not node.linked:
			return False
		doc=MisuraDocument(node.linked.filename)
		from misura.client import archive
		archive.TestWindow(doc).show()
	
	@node	
	def closeFile(self,node=False):
		#FIXME: model no longer have a "tests" structure.
		lk=node.linked
		if not lk:
			print 'Node does not have linked file',node.path
			return False
		for ds in self.doc.data.values():
			if ds.linked==lk:
				self.deleteData(ds)
		self.refresh()
	
	@node
	def reloadFile(self,node=False):
		print 'RELOADING'
		if not node.linked:
			return False
		print node.linked.reloadLinks(self.doc)
		self.refresh()
		
		
	def load_version(self,LF,version):
		#FIXME: VERSIONING!
		print 'LOAD VERSION'
		LF.params.version=version
		LF.reloadLinks(self.doc)
		self.refresh()
		fl=self.model().files
		print 'got linked files',self.model().files[:]
		
	@node	
	def commit(self,node=False):
		"""Write datasets to linked file. """
		name,st=QtGui.QInputDialog.getText(self,"Version Name","Choose a name for the data version you are saving:")
		if not st:
			print 'Aborted' 
			return
		print 'Committing data to',node.filename
		node.commit(unicode(name))
		self.refresh()
		
	###
	# Sample actions
	###
	@node
	def deleteChildren(self,node=False):
		"""Delete all children of node."""
		print 'deleteChildren',node,node.children
		for sub in node.children.values():
			if not sub.ds:
				continue
			self.deleteData(sub)
# 		self.refresh()
		
	@node
	def showPoints(self,node=False):
		"""Show characteristic points"""
		from misura.client import plugin
		p=plugin.ShapesPlugin(sample=node)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.ShapesPlugin)
		self.mainwindow.showDialog(d)
		
	@node
	def report(self,node=False):
		"""Execute ReportPlugin on `node`"""
		from misura.client import plugin
		p=plugin.ReportPlugin(sample=node)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
		self.mainwindow.showDialog(d)
		
	@node
	def render(self,node=False):
		"""Render video from `node`"""
		from misura.client import video
		sh=getFileProxy(node.linked.filename)
		pt=node.path.replace(node.linked.prefix,'').replace('summary','')
		v=video.VideoExporter(sh,pt)
		v.exec_()
		sh.close()
		
	###
	# Dataset actions
	###
	def _load(self, node):
		"""Load or reload a dataset"""
		p=ImportParamsMisura(filename=node.linked.filename,
							rule_exc=' *',
							rule_load=node.m_col+'$',
							rule_unit=clientconf.confdb['rule_unit'])
		op=OperationMisuraImport(p)
		self.doc.applyOperation(op)
	
	@node
	def load(self,node=False):
		print 'load',node
		if node.linked is None:
			print 'Cannot load: no linked file!',node
			return
		if not node.linked.filename:
			print 'Cannot load: no filename!',node
			return
		if len(node.ds)>0:
			print 'Unloading',node.path
			node.ds.data=[]
			self.previous_selection=False
			self.refresh()
			return
		self._load(node)
		self.refresh()
		pass
	
	@node
	def thermalLegend(self,node=False):
		"""Write thermal cycle onto a text label"""
		from misura.client import plugin
		p=plugin.ThermalCyclePlugin(test=node)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.ThermalCyclePlugin)
		self.mainwindow.showDialog(d)
		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)
	
	@node
	def setInitialDimension(self,node=False):
		"""Invoke the initial dimension plugin on the current entry"""
		print 'Searching dataset name',node,node.path
		n=self.doc.datasetName(node.ds)
		ini=getattr(node.ds, 'm_initialDimension', False)
		if not ini: ini=100.
		print 'Invoking InitialDimensionPlugin',n,ini
		from misura.client import plugin
		p=plugin.InitialDimensionPlugin(ds=n, ini=ini)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.InitialDimensionPlugin)
		self.mainwindow.showDialog(d)
# 		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)
		
	@node
	def convertPercentile(self,node=False):
		"""Invoke the percentile plugin on the current entry"""
		n=self.doc.datasetName(node.ds)
		from misura.client import plugin
		p=plugin.PercentilePlugin(ds=n,propagate=True)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.PercentilePlugin)
		self.mainwindow.showDialog(d)
# 		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)
		
	@node
	def set_unit(self,node=False,convert=False):
		print 'set_unit:',node,node.unit,convert
		if node.unit==convert or not convert or not node.unit:
			print 'set_unit: Nothing to do'
			return
		n=self.doc.datasetName(node.ds)
		from misura.client import plugin
		p=plugin.UnitsConverterTool(ds=n,convert=convert,propagate=True)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.UnitsConverterTool)
		self.mainwindow.showDialog(d)
# 		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)
		
	@node
	def deleteData(self,node=False,remove_dataset=True, recursive=True):
		"""Delete a dataset and all depending graphical widgets."""
		ds=node.ds
		pt=node.path
# 		pt=self.doc.datasetName(ds)
		# Exit if no plot is associated
		if not self.model().plots['dataset'].has_key(pt):
# 			n=self.doc.datasetName(ds)
			self.doc.deleteDataset(pt)
			self.doc.setModified()
			self.previous_selection=False
			return
#		self.model().pause(True)
		plots=self.model().plots['dataset'][pt]
		# Collect involved graphs
		graphs=[]
		# Collect plots to be removed
		remplot=[]
		# Collect axes which should be removed
		remax=[]
		# Collect objects which refers to xData or yData
		remobj=[]
		# Remove associated plots
		for p in plots:
			p=self.doc.resolveFullWidgetPath(p)
			g=p.parent
			if g not in graphs: graphs.append(g)
			remax.append(g.getChild(p.settings.yAxis))
			remplot.append(p)
				
		# Check if an ax is referenced by other plots
		for g in graphs:
			for obj in g.children:
				if obj.typename=='xy':
					y=g.getChild(obj.settings.yAxis)
					if y is None: continue
					# If the axis is used by an existent plot, remove from the to-be-removed list
					if y in remax and obj not in remplot: 
						remax.remove(y)
					continue
				# Search for xData/yData generic objects
				
				for s in ['xData','yData','xy']:
					o=getattr(obj.settings,s,None)
					refobj=g.getChild(o)
					if refobj is None:
						continue
					if refobj not in plots+[pt]: 
						continue
					if obj not in remplot+remax+remobj: 
						remobj.append(obj)

		# Remove object and unreferenced axes
		for obj in remplot+remax+remobj:
			print 'Removing obj',obj.name, obj.path
			obj.parent.removeChild(obj.name)
		# Finally, delete dataset
		if remove_dataset:
# 			n=self.doc.datasetName(ds)
			self.doc.deleteDataset(pt)
			print 'deleted', pt
			self.previous_selection=False
		
		#Recursive call over derived datasets
		if recursive:
			for sub in node.children.itervalues():
				self.deleteData(sub,remove_dataset, recursive)
		self.previous_selection=False
		self.doc.setModified()
	
	@nodes	
	def deleteDatas(self,nodes=[]):
		"""Call deleteData on each selected node"""
		for n in nodes:
			self.deleteData(node=n)

	
	def xnames(self, y, page=False):
		"""Get X dataset name for Y node y, in `page`"""
		if page==False:
			page=self.model().page
		print 'XNAMES',y,type(y),y.path
		print 'y.linked', y.linked
		print 'y.parent.linked', y.parent.linked
		lk=y.linked if y.linked else y.parent.linked
		p=getattr(lk,'prefix','')
		if page.startswith('/time'):
			names=[y.linked.prefix+'t']  
		else:
			names=[y.linked.prefix+'summary/kiln/T']
		return names
	
	def dsnode(self,node):
		"""Get node and corresponding dataset"""
		ds=node
		if isinstance(node,DatasetEntry):
			ds=node.ds
		return ds,node
				
	@node	
	def plot(self,node=False):
		"""Slot for plotting by temperature and time the currently selected entry"""
		pt=self.model().is_plotted(node.path)
		if pt:
			print 'UNPLOTTING',node
			self.deleteData(node=node,remove_dataset=False, recursive=False)
			return
		# Load if no data
		if len(node.data)==0:
			self.load(node)
		yname=node.path
		
		from misura.client import plugin
		# If standard page, plot both T,t
		page=self.model().page
		if page.startswith('/temperature/') or page.startswith('/time/'):
			print 'Quick.plot',page
			# Get X temperature names
			xnames=self.xnames(node,page='/temperature')
			assert len(xnames)>0
			p=plugin.PlotDatasetPlugin()
			p.apply(self.cmd,{'x':xnames,'y':[yname]*len(xnames),'currentwidget':'/temperature/temp'})
			
			# Get time datasets
			xnames=self.xnames(node,page='/time')
			assert len(xnames)>0
			p=plugin.PlotDatasetPlugin()
			p.apply(self.cmd,{'x':xnames,'y':[yname]*len(xnames),'currentwidget':'/time/time'})
		else:
			if page.startswith('/report'):
				page=page+'/temp'
			print 'Quick.plot on currentwidget',page
			xnames=self.xnames(node,page=page)
			assert len(xnames)>0
			p=plugin.PlotDatasetPlugin()
			p.apply(self.cmd,{'x':xnames,'y':[yname]*len(xnames),'currentwidget':page})
		self.doc.setModified()
		
	@node
	def edit_dataset(self,node=False):
		"""Slot for opening the dataset edit window on the currently selected entry"""
		ds,y=self.dsnode(node)
		name=ds.name()
		print 'name',name
		dialog=self.mainwindow.slotDataEdit(name)
		if ds is not y:
			dialog.slotDatasetEdit()
#		self.connect(dialog, QtCore.SIGNAL('dialogFinished'), self.refresh)
			
	@node
	def smooth(self,node=False):
		"""Call the SmoothDatasetPlugin on the current node"""
		ds,node=self.dsnode(node)
		w=max(5,len(ds.data)/50)
		from misura.client import plugin
		p=plugin.SmoothDatasetPlugin(ds_in=node.path, ds_out=node.m_name+'_sm', window=int(w))
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.SmoothDatasetPlugin)
		self.mainwindow.showDialog(d)
		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)
		
	@node
	def coefficient(self,node=False):
		"""Call the CoefficientPlugin on the current node"""
		ds,node=self.dsnode(node)
		w=max(5,len(ds.data)/50)
		ds_x=self.xnames(node,'/temperature')[0]
		ini=getattr(ds, 'm_initialDimension', 0)
		from misura.client import plugin
		p=plugin.CoefficientPlugin( ds_y=node.path, ds_x=ds_x, ds_out=node.m_name+'_cf',smooth=w, percent=ini)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.CoefficientPlugin)
		self.mainwindow.showDialog(d)
		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)
		
	@node
	def derive(self,node=False):
		"""Call the DeriveDatasetPlugin on the current node"""
		ds,node=self.dsnode(node)
		w=max(5,len(ds.data)/50)
		ds_x=self.xnames(node)[0] # in current page
		from misura.client import plugin
		p=plugin.DeriveDatasetPlugin( ds_y=node.path, ds_x=ds_x, ds_out=node.m_name+'_d',smooth=w)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.DeriveDatasetPlugin)
		self.mainwindow.showDialog(d)
		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)
	
	@nodes
	def correct(self,nodes=[]):
		"""Call the CurveOperationPlugin on the current nodes"""
		ds0,node0=self.dsnode(nodes[0])
		T0=node0.linked.prefix+'summary/kiln/T'
		ds1,node1=self.dsnode(nodes[1])
		T1=node1.linked.prefix+'summary/kiln/T'
		from misura.client import plugin
		p=plugin.CurveOperationPlugin(ax=T0,ay=ds0.name(),bx=T1,by=ds1.name())
		#TODO: TC comparison?
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.CurveOperationPlugin)
		self.mainwindow.showDialog(d)
		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)	
	
	@nodes
	def surface_tension(self,nodes):
		"""Call the SurfaceTensionPlugin.
		- 1 node selected: interpret as a sample and directly use its beta,r0,Vol,T datasets
		- 2 nodes selected: interpret as 2 samples and search the node having beta,r0 children; use dil/T from the other
		- 4 nodes selected: interpret as separate beta, r0, Vol, T datasets and try to assign based on their name
		- 5 nodes selected: interpret as separate (beta, r0, T) + (dil, T) datasets and try to assign based on their name and path
		"""
		if len(nodes)>1:
			print 'Not implemented'
			return False
		smp=nodes[0].children
		dbeta,nbeta=self.dsnode(smp['beta'])
		beta=dbeta.name()
		dR0,nR0=self.dsnode(smp['r0'])
		R0=dR0.name()
		ddil,ndil=self.dsnode(smp['Vol'])
		dil=ddil.name()
		T=nbeta.linked.prefix+'summary/kiln/T'
		out=nbeta.linked.prefix+'gamma'
		if not self.doc.data.has_key(T):
			T=''
		# Load empty datasets
		if len(dbeta)==0:
			self._load(nbeta)
		if len(dR0)==0:
			self._load(nR0)
		if len(ddil)==0:
			self._load(ndil)
		from misura.client import plugin
		cls=plugin.SurfaceTensionPlugin
		p=cls(beta=beta,R0=R0,T=T,
								dil=dil,dilT=T, ds_out=out)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, cls)
		self.mainwindow.showDialog(d)
		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)			
	@node
	def keep(self,node=False):
		"""Inverts the 'keep' flag on the current dataset, 
		causing it to be saved (or not) on the next file commit."""
		ds,node=self.dsnode(node)
		cur=getattr(ds,'m_keep',False)
		ds.m_keep=not cur
		
	@node
	def colorize(self,node=False):
		"""Set/unset color markers."""
		plotpath = self.model().is_plotted(node.path)
		if not len(plotpath) > 0:
			return False
		x=self.xnames(node)[0]
		from misura.client import plugin
		p=plugin.ColorizePlugin(curve=plotpath[0],x=x)	
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.ColorizePlugin)
		self.mainwindow.showDialog(d)		
	
	@node
	def save_style(self,node=False):
		"""Save current curve color, style, marker and axis ranges and scale."""
		#TODO: save_style
		pass
	
	@node
	def delete_style(self,node=False):
		"""Delete style rule."""
		#TODO: delete_style
		pass	
	
	@node
	def change_rule(self,node=False,act=0):
		"""Change current rule"""
		#TODO: change_rule
		pass
		
		
	####
	# Derived actions
	@node
	def overwrite(self,node=False):
		"""Overwrite the parent dataset with a derived one."""
		ds,node=self.dsnode()
		from misura.client import plugin
		p=plugin.OverwritePlugin(a=node.parent.path,b=node.path,delete=True)
		d = veusz.dialogs.plugin.PluginDialog(self.mainwindow, self.doc, p, plugin.OverwritePlugin)
		self.mainwindow.showDialog(d)
		self.connect(d, QtCore.SIGNAL('dialogFinished'), self.refresh)	
		
