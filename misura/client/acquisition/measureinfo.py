#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from ..graphics import thermal_cycle
from .. import conf, widgets
import status

class MeasureInfo(QtGui.QTabWidget):
	"""Configurazione della misura e dei campioni"""
	def __init__(self, remote, fixedDoc=False,  parent=None):
		self.fromthermalCycleView=False
		self.fixedDoc=fixedDoc
		QtGui.QTabWidget.__init__(self, parent)
		self.setTabPosition(QtGui.QTabWidget.East)
		self.remote=remote
		print 'MeasureInfo paths',remote.parent()._Method__name,remote._Method__name,remote.measure._Method__name
		# Configurazione della Misura
		self.server=remote.parent()
		self.measureView=conf.Interface(self.server,remote.measure, remote.measure.describe(), parent=self)
		# Configurazione Ciclo Termico:
		p=self.remote.parent()
		k=False
		try:
			k=p.kiln['name']
		except:
			pass
		if k:
			self.thermalCycleView=thermal_cycle.ThermalCycleDesigner(remote.parent().kiln, parent=self)
		else:
			self.thermalCycleView=QtGui.QWidget(self)
		self.results=QtGui.QWidget(self)
		self.addTab(self.results, 'Results') #Add a tab to correct inizialization og qTabWidget
		self.nobj=widgets.ActiveObject(self.server, self.remote.measure, self.remote.measure.gete('nSamples'), parent=self)
		self.connect(self.nobj, QtCore.SIGNAL('changed()'), self.refreshSamples)
		self.connect(self, QtCore.SIGNAL("currentChanged(int)"), self.tabChanged)
#		self.nobj.emitOptional=self.refreshSamples
		self.nobj.isVisible=self.isVisible
	
	def tabChanged(self):
		currentTab=self.currentWidget()
		if not currentTab==self.thermalCycleView:
			if self.fromthermalCycleView:
				self.checkCurve()
				self.fromthermalCycleView=False
		else:
			self.fromthermalCycleView=True
	
	def checkCurve(self):
		tbcurveremote = self.thermalCycleView.remote.get('curve')
		tbcurve=[]
		for row in self.thermalCycleView.model.curve(events=True):
			tbrowcurve=[]
			tbrowcurve.append(row[0])
			tbrowcurve.append(row[1])
			tbcurve.append(tbrowcurve)
		if not tbcurve==tbcurveremote:
			r = QtGui.QMessageBox.warning(self, "Changes not saved", 
										"Changes to thermal cycle were not saved! Do you save it now?",  
										QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
			if r==QtGui.QMessageBox.Yes:
				self.thermalCycleView.apply()

	def refreshSamples(self, *foo):
		self.clear()
		if not self.fixedDoc:
			self.statusView=status.Status(self.server, self.remote, parent=self)
			self.addTab(self.statusView, 'Status')
			self.connect(self.statusView.wg_isRunning, QtCore.SIGNAL('changed()'), self.up_isRunning)
			self.up_isRunning()
		self.addTab(self.measureView, 'Measure')
		self.addTab(self.thermalCycleView, 'Thermal Cycle')
		print 'REFRESH SAMPLES', self.remote.measure['nSamples']
		for i in range(self.remote.measure['nSamples']):
			sample=getattr(self.remote, 'sample'+str(i), False)
			if not sample: 
				print 'Missing sample object nr.', i
				continue
			self.addTab(conf.Interface(self.remote.parent(),sample, sample.describe(), self), 'Sample'+str(i))
		self.addTab(self.results, 'Results')
		
		
	def up_isRunning(self):
		if self.statusView.wg_isRunning.current:
			self.tabBar().setStyleSheet("background-color:red;")
		else:
			self.tabBar().setStyleSheet("background-color:green;")
