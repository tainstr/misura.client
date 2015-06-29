#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
from active import ActiveWidget, getRemoteDev
from .. import _
from misura.canon.logger import Log as logging

class Role(ActiveWidget):
	isIO=False
	bmenu_hide=False
	def __init__(self, *a, **k):
		ActiveWidget.__init__(self, *a, **k)
		self.isIO=self.type.endswith('IO')
		self.subwin={} # goto() subwindos mapping
		self.bmenu.setText('None')
		self.bmenu.setMaximumWidth(1000)
		self.emenu.addAction(_('Change'), self.edit)
		self.emenu.addAction(_('Unset'), self.unset)
		self.emenu.addAction(_('Go to'), self.goto)
		self.value=QtGui.QLabel('None')
		self.lay.addWidget(self.value)
		self.emit(QtCore.SIGNAL('selfchanged()'))
		
	def unset(self):
		self.set(['None','default'])
		
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
		if self.isIO:
			return str(val)
		# Evaluate if to shorten the fullpath by adding an ellipsis at the beginning
		if self.current in [None, 'None']:
			return 'None'
		val=val[:]
		d=len(val[0])-20
		if d>4:
			val[0]='...'+val[0][d:]
		r='{}: {}'
		return r.format(*val)
		
	def update(self):
		"""Update text in the button and help tooltip."""
		if self.current in [None, 'None']:
			self.bmenu.setText('None')
			self.bmenu.setToolTip('Error: Undefined value')
			return
		s=self.adapt2gui(self.current)
		self.bmenu.setText(s)
		tt='Object: {}\nPreset: {}'
		tt=tt.format(*self.current)
		self.bmenu.setToolTip(tt)
		self.value.setText(s)
		
	def edit(self):
		"""Opens the Role editing dialog."""
		d=RoleDialog(self)
		return d.exec_()
		

class RoleIO(ActiveWidget):
	isIO=True
	value=None
	def __init__(self, *a, **k):
		ActiveWidget.__init__(self, *a, **k)
		self.subwin={} # goto() subwindos mapping
		self.ioact=self.emenu.addAction('None',self.edit)
		self.emenu.addAction(_('Unset'), self.unset)
		self.emenu.addAction(_('Go to'), self.goto)
		self.value=QtGui.QLabel('None')
		self.update()
		
		self.emit(QtCore.SIGNAL('selfchanged()'))
		
	def update(self):
		""" Draw the referred widget"""
		self.prop=self.remObj.gete(self.handle)
		if not self.prop:
			logging.warning('Cannot get option  %s', self.handle )
			return 
		opt=self.prop['options']
		path=self.server.searchPath(opt[0])
		obj=self.server.toPath(opt[0])
		fu=False
		# Is update needed? 
		if self.value:
			if hasattr(self.value,'prop'):
				kid=opt[0]+opt[-1]
				if kid==self.value.prop['kid']:
					return
				fu=self.value.force_update
			# Remove old widget
			self.lay.removeWidget(self.value)
			self.value.hide()
			self.value.close()
		# Recreate widget
		if path and obj and opt[2] not in ('None',None):
			from misura.client.widgets import build
			self.value=build(self.server,obj,obj.gete(opt[2]))
			self.value.label_widget.hide()
			self.value.force_update=fu
			#TODO: manage units and menu, which is bounded to label_widget
		else:
			self.value=QtGui.QLabel('None')
		self.lay.addWidget(self.value)
		self.ioact.setText('{}: {} : {}'.format(*opt))

	def unset(self):
		self.remObj.setattr(self.handle,'options',['None','default','None'])
		self.update()
		
	def goto(self):
		cur=self.prop['options']
		p=cur[0]
		if p in ['None', None]:
			return False
		# retrieve an existing win
		v=self.subwin.get(p, False)
		if v: 
			v.show()
			return True
		from ..conf import mconf
		obj=self.remObj.root.toPath(cur[0])
		v=mconf.TreePanel(obj, select=obj)
		v.show()
		self.subwin[p]=v
		return True
		
	def  adapt2gui(self, val):
		"""Convert the Role list into a string"""
		return str(val)
		
	def edit(self):
		"""Opens the Role editing dialog."""
		d=RoleDialog(self)
		return d.exec_()
		
	
	
class RoleDialog(QtGui.QDialog):
	def __init__(self, parent):
		QtGui.QDialog.__init__(self, parent=parent)
		self.setWindowTitle(_('Select an object for this Role'))
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
		self.lay.addRow(_('Select object'), self.tree)
		# preset chooser
		self.config=QtGui.QComboBox(parent=self)
		self.lay.addRow(_('Configuration preset'), self.config)
		# IO chooser
		if self.w.isIO:
			self.io=QtGui.QComboBox(parent=self)
			self.lay.addRow(_('Option name'), self.io)
		self.connect(self.tree.selectionModel(), 
					QtCore.SIGNAL('currentChanged(QModelIndex,QModelIndex)'), 
					self.select)
		self.update()
		
	@property
	def current(self):
		if self.w.isIO:
			return self.w.prop['options']
		return self.w.current
		
	def update(self, cur=False, prev=False):
		# Set current values
		devpath=self.current[0]
		objpath=self.w.server.searchPath(devpath)
		logging.debug('%s %s %s', 'server.searchPath', objpath, self.current)
		if objpath is False: 
			return
		# this will emit a currentChanged(), triggering select()
		self.tree.select_path(objpath) 
		
	def select(self, cur=False, prev=False):
		self.remDev=False
		self.redraw_config(cur)
		conf=self.current[1]
		idx=self.config.findData(conf)
		self.config.setCurrentIndex(idx)
		if self.w.isIO:
			io=self.current[2]
			idx=self.io.findData(io)
			self.io.setCurrentIndex(idx)
		
	def redraw_config(self, idx):
		"""Redraw the configuration combobox, reading the possible configurations for the current device."""
		self.config.clear()
		self.config.addItem('default', 'default')
		path=self.tree.current_fullpath()
		st, self.remDev=getRemoteDev(self.w.server, path)
		logging.debug('%s %s %s %s', 'redraw_config Got Remote Dev', self.current[0], path, self.remDev)
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
				logging.debug('%s %s', 'IO Listing', pre)
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
		r=[r, r1]
		if self.w.isIO:
			r.append(r2)
			self.w.remObj.setattr(self.w.handle,'options',r)
			self.w.update()
		else:
			self.w.set(r)
		
		
