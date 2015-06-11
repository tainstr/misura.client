#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from PyQt4 import QtGui, QtCore
import control

	
		
		
class ViewerDialog(QtGui.QDialog):
	def __init__(self, server, remote, parent=None):
		QtGui.QDialog.__init__(self, parent)
		self.setWindowTitle('Camera Viewer: ' + remote['name'])
		self.server=server
		self.remote = remote
		self.control = control.ViewerControl(remote, server,  self)
		self.resizeCam()
		self.connect(self.viewer.processor, QtCore.SIGNAL('fps(float)'), self.updateFPS)
		
		self.lay = QtGui.QVBoxLayout()
		self.setLayout(self.lay)
		
		self.lay.addWidget(self.control)
		
		self.stopButton = QtGui.QPushButton('Close this viewer')
		self.lay.addWidget(self.stopButton)
		self.connect(self.stopButton, QtCore.SIGNAL('clicked()'), self.close)
		self.connect(self, QtCore.SIGNAL('destroyed()'), self.stopStream)
		self.connect(self, QtCore.SIGNAL('accepted()'), self.stopStream)
		self.connect(self, QtCore.SIGNAL('rejected()'), self.stopStream)
		
	@property
	def viewer(self):
		return self.control.viewer
		
	def resizeCam(self):
		#Independency from initial size
		w, h = self.remote.get('size')
		self.w, self.h = w, h
		if w == 0: 
			w = 640; h = 480
		self.r = (1.*h) / w
		h = int(640.*self.r); w = 640
		self.resize(w, h + 80)
		self.viewer.resize(w,h)
		return w,h
		
	def showEvent(self,e):
		self.resizeCam()
		QtGui.QDialog.showEvent(self,e)	
			
	def stopStream(self, *a):
		self.toggle_stream(do=False)
		
	def close(self):
		logging.debug('%s', 'ViewerDialog.close')
		self.toggle_stream(do=False)
		self.viewer.close()
		self.control.close()
		self.done(0)
		
	def updateFPS(self, fps):
		"""Called when the frame-per-second value is updated by Viewer"""
		self.stopButton.setText('Close this viewer - %.2f FPS' % fps)
		#Independency from initial size
		w, h = self.remote.get('size')
		if w == 0: 
			return
		r = (1.*h) / w
		if r != self.r:
			# Adjust dialog height
			logging.debug('%s %s %s', 'Resize dialog to', self.width(), self.width() * r)
			self.resize(self.width(), self.width() * r)
			#Resize the graphics view height
			logging.debug('%s %s %s', 'Resize viewer to', self.viewer.width(), self.viewer.width() * r)
			self.viewer.resize(self.viewer.width(), self.viewer.width() * r)
			self.viewer.userZoom = False
			# Keep current image ratio
			self.w = w; self.h = h; self.r = r
		
	def toggle_stream(self, do=None):
		"""Activate/deactivate camera viewing"""
		logging.debug('%s %s', 'ViewerDialog.toggle_stream', do)
		if not self.viewer:
			return 
		if do == None:
			self.toggle_stream(do=self.viewer.processor.stream ^ 1)
			return
		if do > 0: 
			logging.debug('%s', 'start')
			self.show()
			self.viewer.toggle(do=1)
		else:
			logging.debug('%s', 'stop')
			self.viewer.toggle(do=0)
			self.hide()	

