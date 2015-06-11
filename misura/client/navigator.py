#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
import functools
import logging

import veusz.document as document
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
from misura.client import _
import filedata
import fileui
import units
from clientconf import confdb

class StylesMenu(QtGui.QMenu):
	def __init__(self, doc, node):
		QtGui.QMenu.__init__(self, _('Styles'))
		self.doc = doc
		self.node = node
		self.addAction(_('Colorize'), self.colorize)
		
class Navigator(filedata.QuickOps, QtGui.QTreeView):
	"""List of currently opened misura Tests and reference to datasets names"""
	previous_selection = False
	
	def __init__(self, parent=None, doc=None, mainwindow=None, context='Graphics', menu=True, status=filedata.dstats.loaded, cols=1):
		QtGui.QTreeView.__init__(self, parent)
		self.status = status
		self.ncols = cols
		self._mainwindow = mainwindow
		self.acts_status = []
		self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
		self.setDragEnabled(True)
		self.setAlternatingRowColors(True)
		self.setSelectionBehavior(QtGui.QTreeView.SelectItems)
		self.setSelectionMode(QtGui.QTreeView.ExtendedSelection)
		self.setUniformRowHeights(True)
		
		self.connect(self, QtCore.SIGNAL('clicked(QModelIndex)'), self.select)
		
		# Menu creation
		if menu:
			self.setContextMenuPolicy(Qt.CustomContextMenu)
			self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showContextMenu)
			######
			# Group or No-selection menu
			self.base_menu = QtGui.QMenu(self)
			
			self.acts_status = []
			for i, s in enumerate(filedata.dstats):
				name = filedata.dstats._fields[i]
				act = self.base_menu.addAction(_(name.capitalize()), self.set_status)
				act.setCheckable(True)
				if s == status:
					act.setChecked(True)
				self.acts_status.append(act)
			
			self.act_del=self.base_menu.addAction(_('Delete'), self.deleteChildren)
			self.base_menu.addAction(_('Update view'), self.refresh)

			######
			# File menu
			self.file_menu = QtGui.QMenu(self)
			self.file_menu.addAction(_('Thermal Legend'), self.thermalLegend)
			self.file_menu.addAction(_('Intercept all curves'), self.intercept)
			self.file_menu.addAction(_('View'), self.viewFile)
			self.file_menu.addAction(_('Reload'), self.reloadFile)
			self.file_menu.addAction(_('Close'), self.closeFile)
			self.file_menu.addAction(_('Commit data to test file'), self.commit)
			self.file_menu.addAction(_('Update view'), self.refresh)
			self.ver_menu = self.file_menu.addMenu('Load Version')

			######
			# Sample menu
			self.sample_menu = QtGui.QMenu(self)

			######
			# Dataset menu
			self.dataset_menu = QtGui.QMenu(self)

			######
			# Derived dataset menu
			self.der_menu = QtGui.QMenu(self)
			
			####
			# Binary
			self.bin_menu = QtGui.QMenu(self)
			self.bin_menu.addAction(_('Correct'), self.correct)
			self.bin_menu.addAction(_('Delete selection'), self.deleteDatas)
			
		else:
			self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.refresh)
		if doc:
			self.set_doc(doc)
		
	
	def set_idx(self, n):
		return self.model().set_idx(n)
	
	def set_time(self, t):
		return self.model().set_time(t)
	
	def hide_show(self, *a, **k):
		return self.model().hide_show(*a, **k)
	
	def set_doc(self, doc):
		self.doc = doc
		self.cmd = document.CommandInterface(self.doc)
		self.setWindowTitle(_('Opened misura Tests'))
		self.mod = self.doc.model
		self.mod.ncols = self.ncols
		self.setModel(self.mod)
		self.mod.modelReset.connect(self.restore_selection)
		self.expandAll()
		self.selection = QtGui.QItemSelectionModel(self.model())
		self.set_status()

	def set_status(self):
		final = set()
		for i, s in enumerate(filedata.dstats):
			act = self.acts_status[i]
			if act.isChecked():
				final.add(s)
		if len(final) == 0:
			logging.debug('%s', 'no valid status requested')
			return
		self.status = final
		self.model().status = final
		logging.debug('%s %s', 'STATUS SET TO', final)
		self.collapseAll()
		self.refresh()
		self.expandAll()
		
	def select(self, idx):
		node = self.model().data(idx, role=Qt.UserRole)
		self.previous_selection = node.path
		logging.debug('%s %s', 'select', node)
		self.emit(QtCore.SIGNAL('select()'))
		plotpath = self.model().is_plotted(node.path)
		logging.debug('%s %s %s', 'Select: plotted on', node.path, plotpath)
		if len(plotpath) == 0: return
		wg = self.doc.resolveFullWidgetPath(plotpath[0])
		self.mainwindow.treeedit.selectWidget(wg)
		self.emit(QtCore.SIGNAL('select(QString)'), plotpath[0])
		
	def restore_selection(self):
		"""Restore previous selection after a model reset."""
		if self.model().paused:
			return False
		self.expandAll()
		return False
		logging.debug('%s %s', 'restoring previous selection', self.previous_selection)
		if self.previous_selection:
			node = self.model().tree.traverse(self.previous_selection)
			if not node:
				return
			jdx = self.model().index_path(node)
			n = len(jdx)
			for i, idx in enumerate(jdx):
				if i < n - 1:
					# Expand all parent objects
					self.setExpanded(idx, True)
				else:
					# Select the leaf
					self.selectionModel().setCurrentIndex(jdx[-1], QtGui.QItemSelectionModel.Select)
		else:
			self.expandAll()
			
	##############
	# BASE MENU
	######### 
				
	def update_base_menu(self,node=False):
		self.act_del.setEnabled(bool(node))
		
	##############
	# FILE MENU
	######### 
			
	def update_file_menu(self, node):
		if hasattr(self.ver_menu, 'proxy'):
			self.ver_menu.proxy.close()
						
		self.file_menu.removeAction(self.ver_menu.menuAction())
		LF = node.linked
		if not LF:
			return False
		# Open the file proxy for the menus
		# TODO: restore versions. Reduce opening times and cache this data!
		fp = filedata.getFileProxy(LF.filename)
		fp.set_version(LF.params.version)
		# Add the configuration versions menu
		self.ver_menu = fileui.VersionMenu(fp)
		self.file_menu.addMenu(self.ver_menu)
		# Connect to the reload function
		self.ver_func = functools.partial(self.load_version, LF)
		self.connect(self.ver_menu, QtCore.SIGNAL('version()'), self.ver_func)
		return True
	
	##############
	# SAMPLE MENU
	######### 
	
	def update_sample_menu(self, node):
		self.sample_menu.clear()
		self.sample_menu.addAction(_('Intercept all curves'), self.intercept)
		if '/hsm/' in node.path:
			self.sample_menu.addAction(_('Show Characteristic Points'), self.showPoints)
			# Check minimum conditions for surface tension plugin
			j=0; k=['beta','r0','Vol']
			for kj in k: j+=node.children.has_key(kj)
			if j==len(k):
				self.sample_menu.addAction(_('Surface tension'), self.surface_tension)
			self.sample_menu.addAction(_('Report'), self.report)
			self.sample_menu.addAction(_('Render video'), self.render)
		self.sample_menu.addAction(_('Delete'), self.deleteChildren)
		return self.sample_menu
	
	##############
	# DATASET MENU
	######### 
			
	def add_load(self, node, menu):
		"""Add load/unload action"""
		self.act_load = self.dataset_menu.addAction(_('Load'), self.load)
		self.act_load.setCheckable(True)
		if node.linked is None:
			self.act_load.setVisible(False)
		else:
			self.act_load.setChecked(len(node.ds) > 0)	
		
		
	def add_plotted(self, node, menu):
		"""Add plot/unplot action"""
		self.act_plot = menu.addAction(_('Plot'), self.plot)
		self.act_plot.setCheckable(True)
		plotpath = self.model().is_plotted(node.path)
		self.act_plot.setChecked(len(plotpath) > 0)
		
	def add_percentile(self, node, menu):
		"""Add percentile conversion action"""
		self.act_percent = menu.addAction(_('Set Initial Dimension'), self.setInitialDimension)
		self.act_percent = self.dataset_menu.addAction(_('Percentile'), self.convertPercentile)
		self.act_percent.setCheckable(True)		
		self.act_percent.setChecked(node.m_percent)
			
	def add_keep(self, node, menu):
		"""Add on-file persistence action"""
		self.act_keep = self.dataset_menu.addAction(_('Saved on test file'), self.keep)
		self.act_keep.setCheckable(True)	
		self.act_keep.setChecked(node.m_keep)
		
	def add_unit(self, node, menu):
		"""Add measurement unit conversion menu"""
		self.units = {}
		u = node.unit
		if not u:
			return
		un = menu.addMenu(_('Units'))
		kgroup, f, p = units.get_unit_info(u, units.from_base)
		same = units.from_base.get(kgroup, {u:lambda v: v}).keys()
		logging.debug('%s %s', kgroup, same)
		for u1 in same:
			p = functools.partial(self.set_unit, convert=u1)
			act = un.addAction(_(u1), p)
			act.setCheckable(True)
			if u1 == u:
				act.setChecked(True)
			# Keep reference
			self.units[u1] = (act, p)	
			
	def add_styles(self, node, menu):
		"""Styles sub menu"""
		plotpath = self.model().is_plotted(node.path)
		if not len(plotpath) > 0:
			return
		wg = self.doc.resolveFullWidgetPath(plotpath[0])
		self.style_menu = menu.addMenu(_('Style'))
		self.act_color = self.style_menu.addAction(_('Colorize'), self.colorize)
		self.act_color.setCheckable(True)

		self.act_save_style = self.style_menu.addAction(_('Save style'), self.save_style)
		self.act_save_style.setCheckable(True)
		self.act_delete_style = self.style_menu.addAction(_('Delete style'), self.delete_style)
		if len(wg.settings.Color.points):
			self.act_color.setChecked(True)
		if confdb.rule_style(node.path):
			self.act_save_style.setChecked(True)
			
	def add_rules(self, node, menu):
		"""Add loading rules sub menu"""
		self.rule_menu = menu.addMenu(_('Rules'))
		self.act_rule = []
		self.func_rule = []

		def gen(name,idx):
			f=functools.partial(self.change_rule,act=1)
			act = self.rule_menu.addAction(_(name),f)
			act.setCheckable(True)
			self.act_rule.append(act)
			self.func_rule.append(f)

		gen('Ignore',1)
		gen('Force',2)
		gen('Load',3)
		gen('Plot',4)
		
		# Find the highest matching rule
		r = confdb.rule_dataset(node.path, latest=True)
		if r: r = r[0]
		if r > 0:
			self.act_rule[r - 1].setChecked(True)
		
		
	def update_dataset_menu(self, node):
		istime = node.path == 't' or node.path.endswith(':t')
		logging.debug('%s %s', 'update_dataset_menu', node.path)
		self.dataset_menu.clear()
		if istime:
			self.act_load = False
		else:
			self.add_load(node, self.dataset_menu)
			
		self.add_plotted(node, self.dataset_menu)
		
		self.dataset_menu.addAction(_('Edit'), self.edit_dataset)
		
		self.dataset_menu.addAction(_('Intercept this curve'), self.intercept)
		if istime:
			self.act_percent = False
		else:
			self.add_percentile(node, self.dataset_menu)
			self.dataset_menu.addAction(_('Smoothing'), self.smooth)
			self.dataset_menu.addAction(_('Derivatives'), self.derive)
			self.dataset_menu.addAction(_('Linear Coefficient'), self.coefficient)
			self.add_styles(node,self.dataset_menu)
			self.add_rules(node,self.dataset_menu)
		if '/hsm/sample' in node.path:
			self.dataset_menu.addAction(_('Characteristic points'), self.showPoints)	
		if istime:
			self.act_keep = False
		else:
			self.add_keep(node, self.dataset_menu)
			self.dataset_menu.addAction(_('Delete'), self.deleteData)
			
		self.add_unit(node, self.dataset_menu)
		return self.dataset_menu
	
	##############
	# DERIVED MENU
	######### 		
	def update_derived_menu(self, node):
		self.der_menu.clear()
		self.add_plotted(node, self.der_menu)
		self.der_menu.addAction(_('Edit'), self.edit_dataset)
		self.der_menu.addAction(_('Intercept this curve'), self.intercept)
		self.der_menu.addAction(_('Smoothing'), self.smooth)
		self.der_menu.addAction(_('Derivatives'), self.derive)
		self.der_menu.addAction(_('Linear Coefficient'), self.coefficient)
		self.der_menu.addAction(_('Overwrite parent'), self.overwrite)
		self.add_keep(node, self.der_menu)
		self.der_menu.addAction(_('Delete'), self.deleteData)	
		return self.der_menu
		
	def showContextMenu(self, pt):
		sel = self.selectedIndexes()
		n = len(sel)
		node = self.model().data(self.currentIndex(), role=Qt.UserRole)
		logging.debug('%s %s', 'showContextMenu', node.path)
		if not node.parent:
			self.update_base_menu()
			menu = self.base_menu
		elif node.ds is False:
			# Identify a "summary" node
			if not node.parent.parent:
				self.update_file_menu(node)
				menu = self.file_menu
			# Identify a "sampleN" node
			elif node.name().startswith('sample'):
				menu = self.update_sample_menu(node)
			else:
				self.update_base_menu(node)
				menu = self.base_menu
		# The DatasetEntry refers to a plugin
		elif hasattr(node.ds, 'getPluginData'):
			if n == 2:
				menu = self.bin_menu
			else:
				menu = self.update_derived_menu(node)
		# The DatasetEntry refers to a standard dataset
		elif n == 1:
			menu = self.update_dataset_menu(node)
		elif n == 2:
			menu = self.bin_menu
		# No active selection
		else:
			menu = self.base_menu
		
		#menu.popup(self.mapToGlobal(pt))
		# Synchronous call to menu, otherise selection is lost on live update
		self.model().pause(1)
		menu.exec_(self.mapToGlobal(pt))
		self.model().pause(0)
