#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from .. import widgets

class Status(QtGui.QWidget):
	def __init__(self, server, remObj, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.widgets={}
		#TOD: accept drops
		self.lay=QtGui.QFormLayout()
		self.lay.setLabelAlignment(QtCore.Qt.AlignRight)
		self.lay.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)
		wg=widgets.build(server, server,server.gete('isRunning'))
		self.insert_widget(wg)
		for opt in 'name', 'elapsed':
			wg=widgets.build(server, remObj.measure,remObj.measure.gete(opt))
			self.insert_widget(wg)
		if server.kiln['motorStatus']>=0:
			wg=widgets.build(server, server.kiln,server.kiln.gete('motorStatus'))
			wg.force_update=True
			self.insert_widget(wg)			
		for opt in 'T', 'S','P','Ts','Tk':
			wg=widgets.build(server, server.kiln,server.kiln.gete(opt))
			if wg.type.endswith('IO'):
				wg.value.force_update=True
			else:
				wg.force_update=True
			self.insert_widget(wg)
		n=remObj['devpath']
		opt=False
		if n!='kiln':
			if n=='hsm':
				opt='h'
			elif n in ('vertical', 'horizontal', 'flex'):
				opt ='d'
		if opt:
			for i in range(remObj.measure['nSamples']):
				smp=getattr(remObj, 'sample'+str(i))
				print 'Building widget', smp['fullpath'], opt
				wg=widgets.build(server, smp,smp.gete(opt))
				self.insert_widget(wg)
		self.setLayout(self.lay)

	def insert_widget(self,wg):
		self.widgets[wg.prop['kid']]=wg
		self.lay.addRow(wg.label_widget, wg)
		
	def showEvent(self,event):
		for kid,wg in self.widgets.iteritems():
			if not wg.force_update:
				wg.get()
# 				wg.async_get()
		return super(Status,self).showEvent(event)
