#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *

from presets import PresetManager


class ThermalCycleChooser(PresetManager):
	def __init__(self, remObj, parent=None, context='Option'):
		PresetManager.__init__(self,  remObj, parent=parent, context='Option',
		                       preset_handle='thermalCycle', save_handle='save_cycle', remove_handle='delete_cycle')

		self.bEdit=QtGui.QPushButton('Edit')
		self.bEdit.setMaximumWidth(40)
		self.connect(self.bEdit, QtCore.SIGNAL('clicked()'), self.edit)
		self.lay.addWidget(self.bEdit)

	def edit(self):
		"""Lancio dell'editor di ciclo termico"""
		from ..graphics.thermal_cycle import ThermalCycleDesigner
		self.tcd=ThermalCycleDesigner(self.remObj)
		self.tcd.show()
