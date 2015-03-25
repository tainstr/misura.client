#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
from active import ActiveWidget, getRemoteDev
from aString import aString

class Role(ActiveWidget):
	def __init__(self, *a, **k):
		ActiveWidget.__init__(self, *a, **k)
		self.subwin={} # goto() subwindos mapping
		self.button=QtGui.QPushButton('None')
		self.bmenu=QtGui.QMenu()
		self.bmenu.addAction(self.mtr('Change'), self.edit)
		self.bmenu.addAction(self.mtr('Unset'), self.unset)
		self.bmenu.addAction(self.mtr('Go to'), self.goto)
		self.button.setMenu(self.bmenu)
		self.lay.addWidget(self.button)
		self.isIO=self.type.endswith('IO')
		self.emit(QtCore.SIGNAL('selfchanged()'))
#		self.connect(self.button, QtCore.SIGNAL('clicked()'), self.edit)
		
	def unset(self):
		r=['None','default']
		if self.isIO:
			r.append('None')
		self.set(r)
		
	def goto(self):
		p=self.current[0]
		if p in ['None', None]:
			return False
		# retrieve an existing win
		v=self.subwin.get(p, False)
		if v: 
			v.show()
			return True
		from ..conf import mconf
		obj=self.remObj.root.toPath(self.current[0])
		v=mconf.TreePanel(obj, select=obj)
		v.show()
		self.subwin[p]=v
		return True
		
		
	def  adapt2gui(self, val):
		"""Convert the Role list into a string"""
		# Evaluate if to shorten the fullpath by adding an ellipsis at the beginning
		if self.current in [None, 'None']:
			return 'None'
		val=val[:]
		d=len(val[0])-20
		if d>4:
			val[0]='...'+val[0][d:]
		r='{}: {}'
		if self.isIO:
			r='{}: {} : {}'
		return r.format(*val)
		
	def update(self):
		"""Update text in the button and help tooltip."""
		if self.current in [None, 'None']:
			self.button.setText('None')
			self.button.setToolTip('Error: Undefined value')
			return
		self.button.setText(self.adapt2gui(self.current))
		tt='Object: {}\nPreset: {}'
		if self.isIO:
			tt+='\nOption: {}'
		tt=tt.format(*self.current)
		self.button.setToolTip(tt)
		
	def edit(self):
		"""Opens the Role editing dialog."""
		d=RoleDialog(self)
		r=d.exec_()
		
	
class RoleDialog(QtGui.QDialog):
	def __init__(self, parent):
		QtGui.QDialog.__init__(self, parent=parent)
		self.setWindowTitle(parent.mtr('Select an object for this Role'))
		self.lay=QtGui.QVBoxLayout()
		self.setLayout(self.lay)
		self.wg=parent
		self.editor=RoleEditor(parent)
		self.lay.addWidget(self.editor)
		self.buttons=QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel, 
		                                    parent=self)
		self.connect(self.buttons, QtCore.SIGNAL('accepted()'), self.accept)
		self.connect(self.buttons, QtCore.SIGNAL('rejected()'), self.reject)
		self.lay.addWidget(self.buttons)
		
	def accept(self, *a):
		self.editor.apply()
		return QtGui.QDialog.accept(self, *a)
		
		
class RoleEditor(QtGui.QWidget):
	def __init__(self, role_widget):
		QtGui.QWidget.__init__(self, parent=None)
		self.lay=QtGui.QFormLayout()
		self.setLayout(self.lay)
		self.w=role_widget
		from misura.client.conf import ServerView
		self.tree=ServerView(role_widget.server)
		self.lay.addRow(self.w.mtr('Select object'), self.tree)
		# preset chooser
		self.config=QtGui.QComboBox(parent=self)
		self.lay.addRow(self.w.mtr('Configuration preset'), self.config)
		# IO chooser
		if self.w.isIO:
			self.io=QtGui.QComboBox(parent=self)
			self.lay.addRow(self.w.mtr('Option name'), self.io)
		self.connect(self.tree.selectionModel(), 
					QtCore.SIGNAL('currentChanged(QModelIndex,QModelIndex)'), 
					self.select)
		self.update()
		
	def update(self, cur=False, prev=False):
		# Set current values
		devpath=self.w.current[0]
		objpath=self.w.server.searchPath(devpath)
		print 'server.searchPath',objpath, self.w.current
		if objpath is False: 
			return
		# this will emit a currentChanged(), triggering select()
		self.tree.select_path(objpath) 
		
	def select(self, cur=False, prev=False):
		self.remDev=False
		self.redraw_config(cur)
		conf=self.w.current[1]
		idx=self.config.findData(conf)
		self.config.setCurrentIndex(idx)
		if self.w.isIO:
			io=self.w.current[2]
			idx=self.io.findData(io)
			self.io.setCurrentIndex(idx)
		
	def redraw_config(self, idx):
		"""Redraw the configuration combobox, reading the possible configurations for the current device."""
		self.config.clear()
		self.config.addItem('default', 'default')
		path=self.tree.current_fullpath()
		st, self.remDev=getRemoteDev(self.w.server, path)
		print 'redraw_config Got Remote Dev',self.w.current[0], path, self.remDev
		if st and (self.remDev is not None):
			for pre in self.remDev.listPresets():
				if pre=='default': continue
				self.config.addItem(pre, pre)
		if self.w.isIO: 
			self.redraw_io()
			
	def redraw_io(self):
		"""Redraw the IO combobox, reading the available IO list for the current device."""
		self.io.clear()
		self.io.addItem('None', 'None')
		if self.remDev:
			for pre in self.remDev.iolist():
				print 'IO Listing',pre
				self.io.addItem(pre, pre)
	
	def apply(self):
		"""Reads the comboboxes content and translated in a list to be sent to the server."""
		r,r1,r2=['None','default','None']
		r=self.tree.current_fullpath()
		
		r1=self.config.itemData(self.config.currentIndex())
		if type(r1)==type(''):
			r1=str(r1)
			
		if self.w.isIO:
			r2=self.io.itemData(self.io.currentIndex())
			if type(r2)==type(''):
				r2=str(r2)

		if None in [r, r1,r2]:
			raise BaseException('NoneRequest')
		
		if self.w.isIO:
			print 'Adapt2srv IO',[r,r1,r2]
			r=[r, r1,r2]
		else:
			print 'Adapt2srv',[r,r1]
			r=[r, r1]
		self.w.set(r)
		
		
