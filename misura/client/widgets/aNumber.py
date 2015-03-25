#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtCore,QtGui
from traceback import print_exc
from misura.client.parameters import MAX,MIN
from misura.client.widgets.active import ActiveWidget
import math

class aNumber(ActiveWidget):
	def __init__(self, server, remObj, prop, parent=None,slider_class=QtGui.QSlider):
		ActiveWidget.__init__(self, server, remObj, prop, parent)
		min=self.prop.get('min', None)
		max=self.prop.get('max', None)
		step=self.prop.get('step', False)
		self.divider=1.
		# If max/min are defined, create the slider widget
		self.slider=False
		if None not in [max, min]:
			self.slider = slider_class(QtCore.Qt.Horizontal, self)
			self.lay.addWidget(self.slider)
		# Identify float type from type or current/max/min/step
		if self.type=='Float' or type(0.1) in [type(self.current), type(min), type(max), type(step)]:
			self.double=True
			self.sValueChanged='valueChanged(double)'
			self.spinbox=QtGui.QDoubleSpinBox(parent=self)
		else:
			self.double=False
			self.sValueChanged='valueChanged(int)'
			self.spinbox=QtGui.QSpinBox(parent=self)
		self.spinbox.setKeyboardTracking(False)
		self.lay.addWidget(self.spinbox)
		self.setRange(min, max, step)
		# Connect signals
		if self.readonly:
			if self.slider: 
				self.slider.setEnabled(False)
			self.spinbox.setReadOnly(True)
		else:
			if self.slider: 
				self.connect(self.slider, QtCore.SIGNAL('valueChanged(int)'), self.sliderPush)
			self.connect(self.spinbox, QtCore.SIGNAL(self.sValueChanged), self.boxPush)
#		self.emit(QtCore.SIGNAL('selfchanged()'))
		self.update(minmax=False)
		
	def setOrientation(self, direction):
		if not self.slider:
			return
		sp=[QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.Fixed]
		if direction==QtCore.Qt.Horizontal:
			lay=QtGui.QHBoxLayout()
			self.slider.setOrientation(QtCore.Qt.Horizontal)
			self.setSizePolicy(*sp)
			self.slider.setSizePolicy(*sp)
		else:
			self.slider.setOrientation(QtCore.Qt.Vertical)
			self.setSizePolicy(*sp[::-1])
			self.slider.setSizePolicy(*sp[::-1])
			lay=QtGui.QVBoxLayout()
		# Reposition all items on the new layout
		while True:
			i=self.lay.takeAt(0)
			if i<=0: break
			lay.addWidget(i.widget())
		QtGui.QWidget().setLayout(self.layout())
		self.setLayout(lay)
		self.lay=lay
		
	def boxPush(self, target=None):
		if target==None:
			target=self.spinbox.value()
		if self.double: target=float(target)
		else: target=int(target)
		self.set(target)

	def sliderPush(self, target=None):
		if target==None:
			target=self.slider.value()
		target=target/self.divider
		if self.double: target=float(target)
		else: target=int(target)
		self.set(target)

	def update(self, minmax=True):
		print 'updating',self.prop
#		if self.spinbox.hasFocus():
#			print 'aNumber.update has focus - skipping'
#			return
		self.spinbox.blockSignals(True)
		# Update minimum and maximum
		if self.slider and minmax: 
			self.slider.blockSignals(True)
			self.prop=self.remObj.gete(self.handle)
			self.current=self.prop['current']
			self.setRange( self.prop.get('min', None),  
						self.prop.get('max', None), 
						self.prop.get('step', False))
		# Translate server-side value into client-side units				
		cur=self.adapt2gui(self.current)
		try:
			if self.double: 
				cur=float(cur)
				if cur==0:
					self.spinbox.setDecimals(2)
				elif abs(cur)<1:
					dc=math.log(abs(1./cur), 10)
					dc=int(abs(dc))+2
					self.spinbox.setDecimals(dc)
			else: 
				cur=int(cur)
			self.setRange(self.min,self.max,self.step)
			print 'aNumber.update', self.handle,cur,self.current,self.spinbox.maximum(),self.spinbox.minimum()
			self.spinbox.setValue(cur)
# 			self.setRange(self.min, self.max, self.step)
			if self.slider: 
				self.slider.setValue(int(cur*self.divider))
		except:
			print_exc()
		finally:
			self.spinbox.blockSignals(False)
			if self.slider: 
				self.slider.blockSignals(False)

	def setRange(self, min=None, max=None, step=0):
		step=self.adapt2gui(step)
		cur=self.adapt2gui(self.current)
		self.max,self.min=None,None
		if min!=None and max!=None:
			min=self.adapt2gui(min)
			max=self.adapt2gui(max)
			if not step: 
				step=abs(max-min)/100.
			if self.double:
				min=float(min); max=float(max)
			else:
				min=int(min); max=int(max); step=int(step);
				if step==0: step=1;
			self.min,self.max=min,max
		else:
			if max==None: 
				if self.double:
					max=MAX
				else:
					max=2147483647
			else:
				self.max=max
			if min==None: 
				if self.double:
					min=MIN
				else:
					min=-2147483647
			else: 
				self.min=min
			step=cur/10.
		self.spinbox.setRange(min, max)
		if self.double: 
			self.divider=10.**self.spinbox.decimals()
		else:
			step=int(step)
		if step==0: step=1

		self.step=step
		self.divider=1
		self.spinbox.setSingleStep(step*self.divider)
		print 'aNumber.setRange',self.handle,min,max,step,cur
		if self.slider:
			self.slider.setMaximum(max*self.divider)
			self.slider.setMinimum(min*self.divider)
			self.slider.setSingleStep(step*self.divider)
			self.slider.setPageStep(step*2*self.divider)

class aNumberAction(QtGui.QWidgetAction):
	def __init__(self, server, remObj, prop, parent=None):
		QtGui.QWidgetAction.__init__(self,parent)
		self.w=QtGui.QWidget()
		self.lay=QtGui.QVBoxLayout()
		self.w.setLayout(self.lay)
		self.wdg=aNumber( server, remObj, prop, parent=parent)
		self.lay.addWidget(self.wdg.label_widget)
		self.lay.addWidget(self.wdg)
		self.lay.setContentsMargins(0,0,0,0)
		self.lay.setSpacing(0)
		self.setDefaultWidget(self.w)
		
	def showEvent(self, event):
		self.wdg.get()
		return QtGui.QWidgetAction.showEvent(self, event)
		
