#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from aNumber import aNumber
from active import ActiveObject
from .. import _
class MotorSlider(aNumber):
	def __init__(self, server, remObj, parent=None):
		prop=remObj.gete('goingTo')
		self.started=0
		self.target=0
		self.position=0
		aNumber.__init__(self,server, remObj, prop, parent) #,slider_class=QtGui.QScrollBar)
		self.pos_obj=ActiveObject(server, remObj, remObj.gete('position'))
		self.connect(self.pos_obj, QtCore.SIGNAL('selfchanged'), self.update_position)
		if self.slider:
			self.slider.setTracking(False)
			self.slider.setFocusPolicy(QtCore.Qt.ClickFocus)
			self.slider.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
			self.connect(self.slider, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
		self.label_widget.setSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Maximum)
		self.menu=QtGui.QMenu()
		self.spinact=QtGui.QWidgetAction(self.menu)
		self.spinact.setDefaultWidget(self.spinbox)
		self.labelact=QtGui.QWidgetAction(self.menu)
		self.labelact.setDefaultWidget(self.label_widget)
		self.menu.addAction(self.spinact)
		self.menu.addAction(self.labelact)
		self.cfact=self.menu.addAction(_('Configure'), self.hide_show)
		self.cfact.setCheckable(True)
		self.cf=False
		
	def hide_show(self):
		"""Hide/show configuration dialog"""
		from .. import conf
		if not self.cf:
			self.cf=conf.Interface(self.server, self.remObj)
		if not self.cf.isVisible():
			self.cf.show()
		else:
			self.cf.hide()
		
	def showMenu(self, pt):
		if self.cf:
			self.cfact.setChecked(self.cf.isVisible())
		self.menu.popup(self.mapToGlobal(pt))
		
	def enterEvent(self,e):
		self.update()
		return QtGui.QWidget.enterEvent(self,e)
		
	def setOrientation(self, direction):
		r=aNumber.setOrientation(self, direction)
		# TODO: merge in aNumber?
		if self.slider:
			self.lay.setContentsMargins(0, 0, 0, 0)
			self.lay.setSpacing(0)
			self.slider.setContentsMargins(0, 0, 0, 0)
#			a=direction==QtCore.Qt.Horizontal
#			self.slider.setInvertedAppearance(not a)
#			self.slider.setInvertedControls(a)
		return r
		
	def update_position(self, pos):
		self.update(position=pos)
		
	def update(self, *a, **k):
		if self.slider and self.slider.paused:
			return False
		s=k.pop('position', None)
		if s:
			k['minmax']=False
		r=aNumber.update(self,*a, **k)
		if not hasattr(self, 'menu'):
			print 'MotorSlider not fully initialized'
			return r
		# If 'position' argument was not passed, 
		# force pos_obj to re-register itself
		step=1
		if self.slider:
			step=self.slider.singleStep()
		if s is None:
			self.pos_obj.register()
			s=self.position # keep old value
		d=abs(1.*self.current-self.started)
		if self.target!=self.current:
			self.target=self.current
			self.started=s
		elif self.current==s or d==0:
			self.started=s
			d=0
		if d<=5*step:
			self.started=s
#			self.menu.hide()
			s=100
			# Stop forced updates
#			self.pos_obj.force_update=False
		else:
			s=100*(1-abs(self.current-s)/d)
			# Start forced updates
#			self.pos_obj.force_update=True
		msg='%i%%' % abs(s)
		self.label_widget.label.setText(msg)
		return r
	
class MotorSliderAction(QtGui.QWidgetAction):
	def __init__(self,server,remObj,parent=None):
		QtGui.QWidgetAction.__init__(self,parent)
		self.wdg=MotorSlider(server,remObj)
		self.setDefaultWidget(self.wdg)
		
	def showEvent(self, event):
		self.wdg.get()
		return QtGui.QWidgetAction.showEvent(self, event)
		
