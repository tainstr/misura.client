#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of variables at a given time"""
from misura.client import iutils,filedata
from misura.client import widgets
import functools

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

class RowView(widgets.Linguist,QtGui.QTreeView):
	def __init__(self,parent=None):
		QtGui.QTreeView.__init__(self, parent)
		widgets.Linguist.__init__(self,context='Data')
		self.setUniformRowHeights(True)
		self.devmenu={}
		self.curveMap={}
		# TODO: Menu management
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.show_menu)
		self.menu=QtGui.QMenu(self)
		self.menu.addAction('Update View',self.refresh)
		
	def set_doc(self,doc):
		"""Build the model based on the MisuraDocument `doc`"""
		self.doc=doc
		self.setModel(doc.model)
		self.model().refresh()
		
	def refresh(self):
		self.model().refresh()
		
	def set_idx(self,idx=-1):
		if idx<0: idx=self.model().idx
		self.model().set_idx(idx)
		
	def show_menu(self, pt):
		m=self.model()
		if not self.model():
			self.menu.popup(self.mapToGlobal(pt))
			return
		qi=self.indexAt(pt)
		node=qi.internalPointer()
		print 'show_menu',node
		# Show the node menu
		if node!=None:
			if node.status>0:
				menu=QtGui.QMenu(self)
				menu.addAction(self.mtr('Hide this result'), functools.partial(self.hide_show,node.col))
				menu.popup(self.mapToGlobal(pt))
				return
		# Rebuild the menu
		self.load_map,self.avail_map=self.doc.model.build_datasets_menu(self.menu,self.hide_show)
		# Show only the device menu
		#FIXME: NOT DEFINED!
		if node!=None:
			if self.devmenu.has_key(node.col):
# 				print 'Popping up devmenu',node.col
				self.devmenu[node.col].popup(self.mapToGlobal(pt))
				return
		# Show the entire menu
		print 'show_menu entire'
		self.menu.addAction('Update View',self.model().refresh)
		self.menu.popup(self.mapToGlobal(pt))
		
	def keyPressEvent(self,ev):
		k=ev.key()
		if k!=QtCore.Qt.Key_Delete: 
			return QtGui.QTreeView.keyPressEvent(self,ev)
		qi=self.currentIndex()
		node=qi.internalPointer()
		if node!=None and (node.col in self.model().tree.visible):
			self.hide_show(node.col)
		return QtGui.QTreeView.keyPressEvent(self,ev)
	
	def hide_show(self,col,do=None,emit=True):
		print 'RowView.hide_show',col,do,emit
		m=self.model()
		col=str(col)
		if do==None:
			item=m.tree.traverse(col)
			do=item.status>0
		if do:
			m.show(col)
		else:
			m.hide(col)
		if emit: self.emit(QtCore.SIGNAL('hide_show_col(QString,int)'), col,do)
		self.model().refresh()
		
	def isSectionHidden(self,i):
		"""Mimic the HeaderView api"""
		if isinstance(i,int):
			col=self.model().tree.visible[i]
		ent=self.model().tree.traverse(col)
		return ent.status<=0

