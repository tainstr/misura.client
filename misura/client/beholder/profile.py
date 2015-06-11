#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for image analysis"""
import logging
import numpy
from overlay import Overlay
from PyQt4 import QtGui, QtCore

class Profile(Overlay):
	"""Draw a sequence of points corresponding to option type 'Profile'."""
	def __init__(self,parentItem,Z=2):
		Overlay.__init__(self,parentItem,Z=Z)
		self.opt=set(['profile','roi','xmass','ymass', 'crop'])
		self.path=QtGui.QGraphicsPathItem(parent=self)
		self.path.setPen(self.pen)
		self.color.setAlpha(80)
		self.path.setBrush(QtGui.QBrush(self.color))
		
	def unscale(self,factor):
		Overlay.unscale(self,factor)
		self.path.setPen(self.pen)
		
	def up(self):
		"""Update profile view"""
		if self.moving:
			return False
		if not self.current.has_key('profile'): return
		prf=self.current['profile']
		if len(prf)<3:
			logging.debug('%s %s', "No profile", prf)
			return False
		sz,x,y=prf	
		# Discart malformed profiles
		if len(sz)<2 or len(x)<1 or len(x)!=len(y):
			logging.debug('%s %s', "Malformed profile", prf)
			return False
		# Discart malformed profiles
		if len(x)<=1 or len(x)!=len(y):
			logging.debug('%s %s', "Malformed profile", prf)
			return False
		# Translate points with respect to sample ROI
		rx,ry,rw,rh=self.current['roi']
		self.xpt=numpy.array(x)#+rx
		self.ypt=numpy.array(y)#+ry
		# Convert x,y, vectors into a QPointF list
		lst=list(QtCore.QPointF(ix,self.ypt[i]) for i,ix in enumerate(self.xpt))
		# Append bottom ROI points in order to close the polygon
		lst.append(QtCore.QPointF(rx+rw, ry+rh))
		lst.append(QtCore.QPointF(rx, ry+rh))
		lst.append(QtCore.QPointF(self.xpt[0],self.ypt[0]))
		# Create a QPainterPath and add a QPolygonF
		qpath=QtGui.QPainterPath()
		qpath.addPolygon(QtGui.QPolygonF(lst))
		qpath.setFillRule(QtCore.Qt.WindingFill)
		# Add the path to the scene
		self.path.setPath(qpath)
		return True
		
