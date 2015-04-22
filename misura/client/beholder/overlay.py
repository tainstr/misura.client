#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for image analysis"""
from PyQt4 import QtGui, QtCore
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 125, 125), (125, 125, 0), (125, 0, 125)]*3


class Overlay(QtGui.QGraphicsItem):
	"""Active graphical item, which is connected with remote options. 
	Its position and dimension vary according to remote options, 
	as well as an update of remote options will modify the item."""
	moving=False
	opt=set(['roi', 'crop'])
	def __init__(self,parentItem=None,Z=1):
		QtGui.QGraphicsItem.__init__(self,parent=parentItem)
		self.opt=set([])
		self.color=QtGui.QColor(*colors[Z])
		pen = QtGui.QPen(self.color)
		pen.setWidth(3)
		self.pen = pen
		self.Z = Z
		self.current={}
		self.ovname=self.__class__.__name__+str(Z)
		self.hide()
		
	def dim(self, factor=100, minimum=5):
		"""Factor is part of the sceneRect"""
		r=self.scene().sceneRect()
		s=self.scene().views()[0].transform().m11()
		r=self.parentItem().boundingRect()
		d0=max((r.width(), r.height()))/s
		d=int(max((1.*d0/factor, minimum)))
		return d
		
	@property
	def zoom_factor(self):
		t=self.scene().views()[0].transform()
		print 'zoom_factor'
		print	t.m11(), t.m12(), t.m13()
		print	t.m21(), t.m22(), t.m23() 
		print	t.m31(), t.m32(), t.m33() 
		return abs(t.m11()+t.m21())
	
	def unscale(self,factor):
		w=self.pen.widthF()*1./factor
		self.pen.setWidthF(w)
		
	def blockUpdates(self):
		self.moving = True
	def unblockUpdates(self):
		self.moving = False
		
	def slot_update(self,multiget):
		"""Slot to update current value from a multiget result dispatched by a SampleProcessor."""
		if self.moving: 
			return False
		for opt in self.opt:
			if not multiget.has_key(opt):
				continue
			self.current[opt]=multiget[opt]
		print 'slot_update',self,self.current.keys()
		if self.validate():
			self.up()
			return True
		return False
		
	def up(self):
		"""Redraw using current value."""
		pass
	
	def validate(self):
		for opt in self.opt:
			if not self.current.has_key(opt):
				print 'Validation Failed',self.ovname,self.Z 
				return False
		return True
	
	def boundingRect(self):
		return QtCore.QRectF(0,0,0,0)
#		return self.parentItem().boundingRect()
		
	def paint(self,*a,**kw):
		return None
