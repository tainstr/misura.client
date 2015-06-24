#!/usr/bin/python 
# -*- coding: utf-8 -*-
"""Configuration interface for misura.
Global instrument parametrization and setup."""

from misura.canon.logger import Log as logging
from misura.client import network
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

class Item(object):
	def __init__(self,parent=False,name='server',idx=0):
		self.parent=parent
		self.name=name
		self.idx=idx
		self.title=''
		self._model=False
		self.children=[]
		self.names=[]
	def __len__(self): 
		return len(self.children)
	def __repr__(self):
		return '%s.%i.%i.(%s)' % (self.name,self.idx,len(self.children),self.parent)
		
	@property
	def root(self):
		if self.parent==False:
			return self
		return self.parent.root
		
	@property
	def model(self):
		if self.parent==False:
			return self._model
		return self.root.model
	
	@property
	def path(self):
		"""Recursively rebuilds the path of the node as parent0...parentN.nodename"""
		path=[]
		node=self
		while node.name!='server':
			path=[node.name]+path
			node=node.parent
		logging.debug('%s %s', "path", path)
		return path
	
	def index_path(self,path):
		"""Rebuilds the sequence of indexes needed to reach a path"""
		if isinstance(path,str):
			path=path.split('/')
		if path[0]=='server': path.pop(0)
		node=self
		idx=[]
		for name in path:
			logging.debug('%s %s %s', 'index_path searching', name, node.names)
			if name not in node.names:
				logging.debug('%s %s %s %s', 'NAME NOT FOUND', name, node.name, node.names)
				return False,False
			i=node.names.index(name)
			node=node.children[i]
			idx.append(i)
			logging.debug('%s %s %s %s', 'index_path', name, i, node)
		return idx,node
			
def recursiveModel(base, parent=False, model=False):
	if parent==False: 
		parent=Item()
		model=base.rmodel()
		parent._model=model
	# Caching management
	if model!=base._rmodel:
		base._rmodel=model
	else:
		return base._recursiveModel
	
	for i,(path,name) in enumerate(model.iteritems()):
		if path=='self': 
			parent.title=name
			continue
		item=Item(parent, path,i)
		obj=base.child(path)
		item=recursiveModel(obj,item, model[path])
		parent.children.append(item)
		# was: name
		parent.names.append(path)
	base._recursiveModel=parent
	return parent	
		

class ServerModel(QtCore.QAbstractItemModel):
	ncolumns=2
	def __init__(self,server,parent=None):
		QtCore.QAbstractItemModel.__init__(self,parent)
		self.server=server
		self.header=['Object','Description']
		self.refresh()
		
	def setNcolumns(self,val):
		self.ncolumns=val
		
	def refresh(self):
		self.item=Item(idx=0)
		tree=recursiveModel(self.server)
#		print tree.children
		tree.parent=self.item
		self.item.children.append(tree)
#		print len(self.item)
		self.emit(QtCore.SIGNAL('modelReset()'))
		
	def index_path(self,path):
		"""Returns the sequence of model indexes starting from a path: parent0...parentN.nodename"""
		# Get the full sequence of indexes and the parent node
		idx,node=self.item.children[0].index_path(path)
		logging.debug('%s %s %s %s', 'ServerModel.index_path: FOUND', path, idx, node)
		if not idx:
			return []
#		return self.createIndex(idx[-1], 0, node),idx
		jdx=[]
		jdx.append(self.createIndex(0,0,self.item.children[0]))
		for i in idx:
			logging.debug('%s %s %s', 'indexing', jdx[-1], i)
			jdx.append(self.index(i,0,jdx[-1]))
		return jdx
		
	def nodeFromIndex(self, index):
		if not index.isValid():	
			return self.item
		ptr=index.internalPointer()
		return ptr
	
	def rowCount(self,parent):
		node=self.nodeFromIndex(parent)
		return len(node)
	
	def columnCount(self,parent):
		return self.ncolumns
	
	def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
		if orientation!=QtCore.Qt.Horizontal:
			return 
		if role==QtCore.Qt.DisplayRole:
			return self.header[section]
		
	def index(self, row, column, parent):
		if row<0: return QtCore.QModelIndex()
		node=self.nodeFromIndex(parent)
#		print node,len(node),row
		assert len(node)>row
		idx=self.createIndex(row, column,node.children[row])
		return idx
	
	def parent(self, child):
		row, col=0, 0
		node=self.nodeFromIndex(child)
		if node==None: return QtCore.QModelIndex()
		parent=node.parent
		if parent:
			row=parent.idx
		return self.createIndex(row, col, parent)
	
	def data(self, index, role=QtCore.Qt.DisplayRole):
		col=index.column()
		row=index.row()
		if role not in [Qt.DisplayRole, -1]: 
			return None
		node=self.nodeFromIndex(index)
#		print 'data',node
		if role==-1: return node
#		print 'data',node.name
		if col==0:
			return node.name
		elif col==1:
			return node.title
		else:
			return None
	
class ServerView(QtGui.QTreeView):
	def __init__(self,server=False,parent=None):
		QtGui.QTreeView.__init__(self, parent)
		if not server: server=network.manager.remote
		self.treemodel=ServerModel(server, self)
		self.setModel(self.treemodel)
		self.setUniformRowHeights(True)
		self.server=server
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showContextMenu)
		self.menu=QtGui.QMenu(self)
		
		self.menu.addAction('Open',self.objOpen)
		self.menu.addAction('Open in New Tab',self.objNewTab)
		self.menu.addAction('Object Table',self.objTable)
		self.menu.addAction('Update View',self.update)
		self.expandToDepth(0)
		
	@property
	def ncolumns(self):
		self.model().ncolumns()
	@ncolumns.setter
	def ncolumns(self,val):
		self.model().setNcolumns(val)
		
	def select_path(self, path):
		"""Select fullpath object `path`"""
		jdx=self.model().index_path(path)
		n=len(jdx)
		for i, idx in enumerate(jdx):
			if i<n-1:
				# Expand all parent objects
				self.setExpanded(idx, True)
			else:
				# Select the leaf
				self.selectionModel().setCurrentIndex(jdx[-1], QtGui.QItemSelectionModel.Select)
				
	def current_fullpath(self):
		idx=self.selectionModel().currentIndex()
		path=self.model().nodeFromIndex(idx).path
		path='/'.join(path)
		path='/'+path+'/'
		return path
		
	def update(self):
		self.model().refresh()
		self.expandToDepth(0)
		
	def showContextMenu(self, pt):
		self.menu.popup(self.mapToGlobal(pt))
		
	def objOpen(self):
		self.emit(QtCore.SIGNAL('activated(QModelIndex)'),self.currentIndex())
	def objNewTab(self):
		self.emit(QtCore.SIGNAL('objNewTab(QModelIndex)'),self.currentIndex())
		
	def objTable(self):
		self.objOpen()
		self.emit(QtCore.SIGNAL('objTable(QModelIndex)'),self.currentIndex())
