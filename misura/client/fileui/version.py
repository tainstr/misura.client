#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Versioning management utilities"""
from misura.client import widgets
import functools
from PyQt4 import QtGui, QtCore

class VersionMenu(QtGui.QMenu,widgets.Linguist):
	"""Available object versions menu"""
	versionChanged=QtCore.pyqtSignal(('QString'))
	
	def __init__(self,proxy,parent=None):
		QtGui.QMenu.__init__(self,parent=parent)
		widgets.Linguist.__init__(self, 'Local')
		self.setTitle(self.mtr('Version'))
		self.proxy=proxy
		self.redraw()
		self.connect(self,QtCore.SIGNAL('aboutToShow()'),self.redraw)
		
	def redraw(self):
		self.clear()
		vd=self.proxy.get_versions()
		print 'Got info',vd
		if vd is None:
			return
		cur=self.proxy.get_version()
		print 'Current version',cur
		self.loadActs=[]
		for v,info in vd.iteritems():
			print 'Found version',v,info
			p=functools.partial(self.load_version,v)
			act=self.addAction(' - '.join(info),p)
			act.setCheckable(True)
			if v==cur:
				act.setChecked(True)
			# Keep in memory
			self.loadActs.append((p,act))		
		act=self.addAction(self.mtr('New version'),self.new_version)
		self.loadActs.append((self.new_version,act))
		act=self.addAction(self.mtr('Save configuration'),self.save_version)
		self.loadActs.append((self.save_version,act))
		self.actValidate=self.addAction(self.mtr('Check signature'),self.signature)
		
	def load_version(self,v):
		"""Load selected version"""
		self.proxy.set_version(v)
		self.versionChanged.emit(self.proxy.get_version())
		
	def save_version(self):
		"""Save configuration in current version"""
		# Try to create a new version
		if self.proxy.get_version()=='':
			if not self.new_version():
				QtGui.QMessageBox.critical(self,self.mtr("Not saved"),self.mtr("Cannot overwrite original version"))
				return False
		self.proxy.save_conf()
		self.proxy.flush()
		return True
		
	def new_version(self):
		"""Create a new version"""
		name,st=QtGui.QInputDialog.getText(self, self.mtr('Version name'), self.mtr('Choose a name for this version'))
		if not st: return False
		self.proxy.create_version(unicode(name))
		return True
	
	def signature(self):
		"""Check file signature"""
		r=self.proxy.verify()
		if not r:
			QtGui.QMessageBox.critical(self,self.mtr("Signature check failed"),self.mtr("Test data cannot be trusted."))
		else:
			QtGui.QMessageBox.information(self,self.mtr("Signature check succeeded"),self.mtr("Test data is genuine."))

		
