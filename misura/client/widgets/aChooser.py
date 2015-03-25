#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui,QtCore
from misura.client.widgets.active import ActiveWidget


class aChooser(ActiveWidget):
	tuplelike=False
	"""If data passed to combobox are tuple, they must be converted into list an back"""
	
	def __init__(self, server, path, prop, parent=None):
		ActiveWidget.__init__(self, server, path,  prop, parent)
		self.combo=QtGui.QComboBox()
		self.redraw(reget=False)
		self.lay.addWidget(self.combo)
		self.connect(self.combo,  QtCore.SIGNAL('currentIndexChanged(int)'), self.set)

	def redraw(self, reget=True):
		self.combo.blockSignals(True)
		# Cleans combo entries
		for i in range(self.combo.count()):
			self.combo.removeItem(self.combo.currentIndex())
		# Get new property
		self.prop=self.remObj.gete(self.handle)
		print 'aChooser.redraw', self.prop
		opt=self.prop.get('options',[])
		vals=self.prop.get('values', opt)
		# Associate opt-val couples to new combo entries
		for i  in range(len(opt)):
			k=opt[i]
			v=vals[i]
			if isinstance(v,tuple):
				self.tuplelike=True
				v=list(v)
			if type(k)==type(''):
				k=self.tr(k)
			elif type(k)!=type(u''):
				k=str(k)
				K=self.tr(k)
			print 'Combo addItem',k,v
			self.combo.addItem(k, v)
		# Read again the current options, if requested
		if reget: self.get()
		self.update()
		# Restore signals
		self.combo.blockSignals(False)

	def adapt2srv(self, idx):
		"""Translates combobox index into server value"""
		r=self.combo.itemData(idx)
		if isinstance(r,str):
			r=str(r)
		elif self.tuplelike:
			r=tuple(r)
		print 'adapt2srv', idx,r
		return r

	def adapt2gui(self, val):
		"""Translates server value into corresponding combobox index"""
		if self.tuplelike:
			val=list(val)
		r=self.combo.findData(val)
		print 'adapt2gui', repr(self.current), r
		return r

	def update(self):
		idx=self.adapt2gui(self.current)
		print 'update', repr(self.current), idx
		self.combo.setCurrentIndex(self.adapt2gui(self.current))
