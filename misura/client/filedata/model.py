#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Rich, hierarchical representation of opened tests and their datasets"""
import sip
sip.setapi('QString', 2)
from veusz import document
import veusz.setting
import veusz.utils
from .. import _
from entry import DatasetEntry

from PyQt4 import QtCore,QtGui
from PyQt4.QtCore import Qt
import functools
from misura.client.iutils import namingConvention
from misura.canon.csutil import find_nearest_val
from entry import iterpath, NodeEntry,dstats
import collections

from misura.client.iutils import get_plotted_tree


def ism(obj,cls):
	return getattr(obj,'mtype',False)==cls.mtype


def resolve_plugin(doc,ds,ent,name=False):
	# Check if already present
	r=ent.get(id(ds), False)
	if r is not False:
		return ent, r
	# Create a main DatasetEntry instance
	if not isinstance(ds,document.datasets.Dataset1DPlugin):
		entry=DatasetEntry(doc,ds)
		ent[entry.mid]=entry
		return ent, entry
	return ent, False


	
def print_datasets(entry,pre):
	"""Recursive datasets printing"""
	for sub in entry.children.itervalues():
		print pre,sub.name()
		print_datasets(sub,pre+'\t')

def print_ent(ent):
	for name,ds in ent.iteritems():
		print ds.path, id(ds.ds)
		print_datasets(ds,'\t')

from veusz.setting import controls
void=None
voididx=QtCore.QModelIndex()
class DocumentModel(QtCore.QAbstractItemModel):
	changeset=0
	_plots=False
	def __init__(self, doc, status=dstats,refresh=True,cols=2):
		QtCore.QAbstractItemModel.__init__(self)
		self.ncols=cols
		self.status=status
		self.doc=doc
		self.tree=NodeEntry()
		if refresh:
			self.refresh()
		else:
			self.tree=self.doc.model.tree
		controls.Marker._generateIcons()
		controls.LineStyle._generateIcons()
		
	idx=0
	def set_idx(self,t):
		if self.paused:
			return False
		print 'DocumentModel.set_idx',t
		#TODO: convert to time index
		tds=self.doc.data.get('t',False)
		if tds is False: 
			return False 
		n=find_nearest_val(tds.data,t)
		self.idx=n
# 		self.emit(QtCore.SIGNAL('dataChanged(QModelIndex,QModelIndex)'),self.index(0,1),self.index(n,1))
		self.emit(QtCore.SIGNAL('modelReset()'))
		return True
		
	def set_time(self,t):
		"""Changes current values to requested time `t`"""
		idx=find_nearest_val(self.doc.data['t'].data, t, seed=self.idx)
		print 'Setting time t',t,idx
		self.set_idx(idx)
		return True
		
	paused=False
	def pause(self,do=True):
		print 'Set paused',do
		self.paused=do
		if do:
			self.disconnect(self.doc,QtCore.SIGNAL("sigModified"),self.refresh)
		else:
			self.connect(self.doc, QtCore.SIGNAL("sigModified"), self.refresh)
		
	page='/temperature/temp'
	def set_page(self,page):
		if self.paused:
			return False
		if page.startswith('/temperature'):
			page='/temperature/temp'
		elif page.startswith('/time'):
			page='/time/time'
		self.page=page
		self.emit(QtCore.SIGNAL('modelReset()'))
		return True
		
	@property 
	def plots(self):
		if self.changeset!=self.doc.changeset or self._plots is False:
			self._plots=get_plotted_tree(self.doc.basewidget)
			self.changeset=self.doc.changeset
		return self._plots
		
		
	def refresh(self,force=False):
		if not force:
			if self.paused:
				print 'NOT REFRESHING MODEL',self.paused
				return
			elif self.changeset==self.doc.changeset:
				print 'NOTHING CHANGED',self.changeset,self.doc.changeset
				return
		print 'REFRESHING MODEL',self.paused
		self.paused=True
		self.doc.suspendUpdates()
		self.emit(QtCore.SIGNAL('beginResetModel()'))
		
		# New-style tree management
		self.tree.set_doc(self.doc)
		
		self.emit(QtCore.SIGNAL('endResetModel()'))
		self.paused=False
		print 'End reset model sent'
		self.emit(QtCore.SIGNAL('modelReset()'))
		print 'Model reset sent'
		self.changeset=self.doc.changeset
		self.doc.enableUpdates()
		
	def is_plotted(self,key,page=False):
		plots=self.plots['dataset'].get(key,[])
		out=[]
		if not page: page=self.page
		for p in plots:
			if p.startswith(page):
				out.append(p)
		return out
		
	def nodeFromIndex(self, index):
		if index.isValid():	
			return index.internalPointer()
		else:
# 			print 'nodeFromIndex invalid',index.row(),index.column(),index.internalPointer()
			return self.tree
		
	def rowCount(self, parent):
		node=self.nodeFromIndex(parent)
		rc=len(node.recursive_status(self.status, depth=0))
		return rc
	
	def columnCount(self, parent):
		return self.ncols 
		
	
	def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
		if orientation!=QtCore.Qt.Horizontal:
			return 
		if role==QtCore.Qt.DisplayRole:
			if section==0:
				return _('Dataset')
			#TODO!
			return _('Value')
		
	def decorate(self,ent,role):
		"""Find text color and icon decorations for dataset ds"""
		if not ent.ds:
			return void
		plotpath=self.is_plotted(ent.path)
		if len(plotpath)==0: 
			plotwg=False
		else: 
			plotwg=self.doc.resolveFullWidgetPath(plotpath[0])
		
		if role==Qt.DecorationRole:
			# No plots
			if plotwg is False: 
				return void
			# No marker
			mkr=plotwg.settings.get('marker').val
			if mkr is False: 
				return void
			if mkr=='none':
				# Retrieve line style instead
				style=plotwg.settings.get('PlotLine').get('style').val
#					print 'GOT STYLE',node.m_var,style
				i=veusz.setting.LineStyle._linestyles.index(style)
				return controls.LineStyle._icons[i]
			# Other markers
			i=veusz.utils.MarkerCodes.index(mkr)
			return controls.Marker._icons[i]
		if role==Qt.ForegroundRole:
			if plotwg is False: 
				return void
			# Retrieve plot line color
			xy=plotwg.settings.get('PlotLine').get('color').color()
#				print ' ForegroundRole' ,node.m_var,xy.value()
			return QtGui.QBrush(xy)		
		return void

	def data(self, index, role=QtCore.Qt.DisplayRole):
		if role not in [Qt.DisplayRole, Qt.ForegroundRole, Qt.DecorationRole, Qt.UserRole]: 
			return void
		col=index.column()
		row=index.row()
		node=self.nodeFromIndex(index)	
		if role==Qt.UserRole: 
			return node
		if col==0:
			if role in [Qt.ForegroundRole, Qt.DecorationRole]:
				return self.decorate(node,role)
			if isinstance(node, DatasetEntry):
				if role==Qt.DisplayRole:
					s='curve:'+node.path.replace('summary/','')
					t=_(s)
					if s==t: t=node.legend
					return t
			elif isinstance(node,NodeEntry):
				r=node.name()
				LF=node.linked
				if (node.parent and LF) and not node.parent.parent:
					r=getattr(LF.conf,LF.instrument)
					r=r.measure['name']
					if len(LF.prefix):
						r+=', ({})'.format(LF.prefix)
				if role==Qt.DisplayRole:
					return r
				return void

		else:
			if isinstance(node, DatasetEntry):
				d=node.ds.data
				if len(d)>self.idx:
#					print 'Retrieving data index',self.idx
					return str(node.ds.data[self.idx])
		return void
		
	def index(self, row, column, parent=voididx):
		parent=self.nodeFromIndex(parent)
		if not (isinstance(parent, DatasetEntry) or isinstance(parent,NodeEntry)):
			print 'child ERROR',parent
			return voididx
		assert row>=0
		lst=parent.recursive_status(self.status,depth=0)
		if row>=len(lst):
			print 'WRONG ROW',row,len(lst)
			return voididx
		assert row<len(lst), 'index() '+str(parent)+str(row)+str(lst)+str(self.status)
		child=lst[row]
		# Update entries dictionary ???
		self.doc.ent[id(child)]=child
		idx=self.createIndex(row, column, child)
		return idx
		
	def parent(self, child):
		child=self.nodeFromIndex(child)
		if not (isinstance(child, DatasetEntry) or isinstance(child,NodeEntry)):
# 			print 'parent ERROR',child,type(child)
			return voididx
		parent=child.parent
		if parent is False:
# 			print  'parent ERROR no parent',child,child.parent
			return voididx
		# Grandpa
		sup=parent.parent
		if sup is False:
# 			print 'parent ERROR no grandpa'
			return voididx
		lst=sup.recursive_status(self.status,depth=0)
		if parent not in lst:
# 			print 'parent() child not in list',child.path,[d.path for d in lst]
			return voididx
		# Position of parent in grandpa
		row=lst.index(parent)
		return self.createIndex(row, 0, parent)
	
	def indexFromNode(self,node):
		"""Return the model index corresponding to node. Useful in ProxyModels"""
		parent=self.parent(node)
		row=parent.recursive_status(self.status,depth=0).index(node)
# 		row=parent.children.values().index(node)
		return self.createIndex(row,0,parent)
	
	def index_path(self,node):
		"""Returns the sequence of model indexes starting from a node."""
		obj=node
		n=[]
		while obj!=self.tree:
			n.append(obj)
			obj=obj.parent
			if obj is None:
				break

		n.reverse()
		
		jdx=[self.createIndex(0,0,self.tree)]
		for obj in n:
			# Find position in siblings
			i=obj.parent.recursive_status(self.status,depth=0).index(obj)
			# Create index
			jdx.append(self.index(i,0,jdx[-1]))
			
		print 'index_path',jdx
		return jdx
		
	#####
	# Drag & Drop
	def mimeTypes(self):
		return ["text/plain"]
	
	def mimeData(self,indexes):
		out=[]
		for index in indexes:
			node=self.nodeFromIndex(index)
			out.append(node.path)
		print 'mimeData',out
		dat=QtCore.QMimeData()
		dat.setData("text/plain", ';'.join(out))
		return dat
	
	def flags(self,index):
		f=QtCore.QAbstractItemModel.flags(self,index)
		node=self.nodeFromIndex(index)
		if isinstance(node,DatasetEntry):
			return QtCore.Qt.ItemIsDragEnabled | f
		return f
		

	#######################################
	##### FROM HIERARCHY
	#TODO: adapt or move to QuickOps
	def hide(self,name):
		item=self.tree.traverse(name)
		if item.status==dstats.hidden:
			return False
		item.status=0
		return True
		
	def show(self,name):
		item=self.tree.traverse(name)
		if item.status==dstats.visible:
			return False
		item.status=1
		return True
		
	def load(self,name):
		item=self.traverse(name)
		if item.status>dstats.available:
			return False
		item.status=0
		return True
	
	def hide_show(self,col,do=None,emit=True):
		print 'RowView.hide_show',col,do,emit
		col=str(col)
		if do==None:
			item=self.tree.traverse(col)
			do=item.status>0
		if do:
			self.show(col)
		else:
			self.hide(col)
		if emit: self.emit(QtCore.SIGNAL('hide_show_col(QString,int)'), col,do)
		self.model().refresh()
		
	############
	# Menu creation utilities
	
	def build_datasets_menu(self, menu, func, checkfunc=False):
		"""Builds a hierarchical tree menu for loaded datasets. 
		Menu actions will trigger `func`, and their checked status is provided by `checkfunc`."""
		self.refresh()
		menu.clear()
		curveMap={}
		for name,ds in self.doc.data.iteritems():
			if len(ds.data)==0: continue
			func1=functools.partial(func,name)
			self.add_menu(name, menu, func1, curveMap, checkfunc=checkfunc)
			
		# Prepare the 'More...' menu, but not actually populate it until hovered
		more=menu.addMenu('More...')
		bam=lambda: self.build_available_menu(more,func,checkfunc)
		more.connect(more,QtCore.SIGNAL('aboutToShow()'),bam)
		alterMap={'more':more,'bam':bam} # keep references
		
		#NOTICE: must keep these referenced by the caller
		return curveMap, alterMap
	
	def build_available_menu(self,menu,func, checkfunc=lambda ent: ent.status>1):
		"""Builds a menu of available (but empty) datasets, which can be loaded upon request by calling `func`. 
		Their action checked status might is provided by `checkfunc`."""
		menu.clear()
		curveMap1={}
		for name,ds in self.doc.data.iteritems():
			if len(ds.data)>0: continue
			func1=functools.partial(func,name)
			self.add_menu(name, menu, func1, curveMap1,checkfunc=lambda foo: False)		
		#NOTICE: must keep these referenced by the caller
		return curveMap1
	
	splt='/'
	def add_menu(self,name, menu, func=lambda:0, curveMap={},hidden_curves=[],checkfunc=False):
# 		print 'add_menu pre',name,curveMap
		if checkfunc is False:
			def checkfunc(ent):
				return self.plots['dataset'].has_key(name)
		var,smp=namingConvention(name,splt=self.splt)
		# Do not show hidden curves
		if var in hidden_curves:
			return False
		# Recursively create parent menus
		for sub,parent,leaf in iterpath(name):
			if leaf is True:
				break
			if not parent:
				child=sub
			else:
				child=self.splt.join([parent,sub])
			m=curveMap.get(child,False)
			if m is False:
# 				print 'creating intermediate menu',sub,child
				m=menu.addMenu(sub)
				curveMap[child]=m
			menu=m
		act=menu.addAction(sub, func)
		act.setCheckable(True)
		act.setChecked(checkfunc(name))
# 		print 'add_menu',name,sub,parent,curveMap
		return act
	
	def matching(self,pt):
		"""Get the matching axes list"""
		s=self.doc.resolveFullSettingPath(pt+'/match')
		m=s.get()
		if m=='':			m=[]
		elif ',' in m:		m=m.split(',')
		elif ';' in m:		m=m.split(';')
		else: 				m=[m]	
		return m
	
	def build_axes_menu(self, menu):
		"""Builds a two-level hierarchy from all visible axes in a plot. 
		The first level contains axes which does not match any other ax (match setting is empty).
		The second level contains both any other non matched axis, and every other axis 
		which matches the parent first level axis."""
		menu.clear()
		axs=self.plots['axis'].keys()
		print 'AXES',axs
		#TODO: generalize
		axmap={}
		axs1=[] # First level (no match setting)
		axs2={}	# Second level (matching)
		# Populate first-level menu
		for pt in axs:
			# discard axis not in current page
			if not pt.startswith(self.page): 
				print 'Ax: Other page',pt,self.page
				continue
			lst=self.matching(pt)
			if len(lst)==0:
				axmap[pt]=menu.addMenu(pt.replace(self.page+'/',''))
				axs1.append(pt)
				continue
			axs2[pt]=lst
			
		# Populate second-level menu with assigned
		for pt2,lst in axs2.iteritems():
			# Add the matched ax to each other first-level matching ax
			for pt in lst:
				# Skip if not first-level
				if not axmap.has_key(pt): 
					continue
				func=functools.partial(self.match_axes,pt,pt2)
				act=axmap[pt].addAction(pt2.replace(self.page+'/',''),func)
				act.setCheckable(True)
				act.setChecked(True)
			
		# Add unassigned to second level menus
		for pt,menu in axmap.iteritems():
			for pt1 in axs1:
				if pt==pt1: continue
				func=functools.partial(self.match_axes,pt,pt1)
				act=menu.addAction(pt1.replace(self.page+'/',''),func)
				act.setCheckable(True)
				act.setChecked(False)
		#NOTICE: must keep these referenced by the caller
		return axmap
	
	def match_axes(self,first,second):
		"""Add `first`-level axis to the list of matched axes of the `second`-level axis.
		The first-level axis will remain first-level. 
		The `second` will become `second`-level and will be listed 
		in every other first-level axis referenced in its match setting."""
		lst=self.matching(second)
		print 'matching ',first,second,lst
		# Add match
		if first not in lst:
			lst.append(first)
		# Remove match
		else:
			lst.remove(first)
		s=self.doc.resolveFullSettingPath(second+'/match')
		s.set(', '.join(lst))

