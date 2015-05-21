#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from aChooser import aChooser
from .. import _

class PresetManager(aChooser):
	def __init__(self, remObj, parent=None, context='Option',
	             preset_handle='preset', save_handle='save', remove_handle='remove'):

		aChooser.__init__(self, remObj, remObj, remObj.gete(preset_handle), parent=parent)
		self.preset_handle=preset_handle
		self.save_handle=save_handle
		self.remove_handle=remove_handle
		#TODO: make a menu, add Rename, View, etc
		self.bSave=QtGui.QPushButton(_('Save'))
		self.bSave.setMaximumWidth(40)
		self.connect(self.bSave, QtCore.SIGNAL('clicked(bool)'), self.save_current)

		self.bDel=QtGui.QPushButton(_('Del'))
		self.bDel.setMaximumWidth(40)
		self.connect(self.bDel, QtCore.SIGNAL('clicked(bool)'), self.remove)

		self.lay.addWidget(self.bSave)
		self.lay.addWidget(self.bDel)

		self.prevIdx=0

	def add(self, *args):
		n, ok=QtGui.QInputDialog.getText(self, _("Save as..."),
									_("Specify new preset name:"),
									QtGui.QLineEdit.Normal,'default')
		if ok:
			r=self.remObj.call(self.save_handle, str(n))
		else:
			self.combo.setCurrentIndex(self.prevIdx)
		self.redraw()

	def remove(self):
		i=self.combo.currentIndex()
		self.combo.setCurrentIndex(0)
		self.remObj.call(self.remove_handle,
		                 self.adapt2srv(i))
		self.redraw()

	def save_current(self):
		self.remObj.call(self.save_handle,
		                 self.adapt2srv(self.combo.currentIndex()))

	def redraw(self, *args, **kwargs):
		"""Overload per introdurre la voce speciale +Add al termine della lista"""
		# First calls standard redraw
		aChooser.redraw(self, *args, **kwargs)
		# Then adds +Add special entry
		self.combo.blockSignals(True)
		self.combo.addItem('+Add')
		if self.combo.count()<=1:
			self.connect(self.combo, QtCore.SIGNAL('highlighted(int)'), self.add)
		else:
			self.disconnect(self.combo, QtCore.SIGNAL('highlighted(int)'), self.add)
		self.combo.blockSignals(False)

	def set(self, *args):
		"""Overload per filtrare la voce speciale +Add"""
		if self.combo.currentText()=='+Add':
			self.add()
		else:
			self.prevIdx=self.combo.currentIndex()
			aChooser.set(self, *args)
