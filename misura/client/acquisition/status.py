#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from .. import conf, widgets

class Status(QtGui.QWidget):
	def __init__(self, server, remObj, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.lay=QtGui.QFormLayout()
		self.lay.setLabelAlignment(QtCore.Qt.AlignRight)
		self.lay.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)
		wg=widgets.build(server, server,server.gete('isRunning'))
		self.wg_isRunning=wg
		self.lay.addRow(wg.label_widget, wg)
		for opt in 'name', 'elapsed':
			wg=widgets.build(server, remObj.measure,remObj.measure.gete(opt))
			self.lay.addRow(wg.label_widget, wg)
		if server.kiln['motorStatus']>=0:
			wg=widgets.build(server, server.kiln,server.kiln.gete('motorStatus'))
			wg.force_update=True
			self.lay.addRow(wg.label_widget, wg)			
		for opt in 'T', 'P', 'S','Ts','Tk':
			wg=widgets.build(server, server.kiln,server.kiln.gete(opt))
			wg.force_update=True
			self.lay.addRow(wg.label_widget, wg)
		n=remObj['devpath']
		opt=False
		if n!='kiln':
			if n=='hsm':
				opt='h'
			elif n in ('vertical', 'horizontal', 'flex'):
				opt ='d'
			if opt:
				for i in range(remObj['nSamples']):
					smp=getattr(remObj, 'sample'+str(i))
					wg=widgets.build(server, smp,smp.gete(opt))
					self.lay.addRow(wg.label_widget, wg)
		self.setLayout(self.lay)
