#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from misura.client import conf,_
import picture
import dialog
import sys

class ViewerControl(QtGui.QWidget):
	"""A viewer widget with the possibility to add lateral sliders."""
		# Layout: 3 cols 3 rows. Upper/bottom-left/right cells remains empty 
		# (1.1,1.3,3.1,3.3).
	positions={'bottom': (3,2), 'up': (1,2),
			'left': (2,1), 'right': (2,3)}
	"""Default grid coordinates for widgets placing"""
	
	def __init__(self, remote, server, parent=None):	
		QtGui.QWidget.__init__(self, parent)
		self.setWindowTitle('Camera Viewer: ' + remote['name'])
		self.controls={'bottom': None, 'up': None,
				'left': None, 'right': None}
		"""Keeps track of the control widgets positions"""
		self.server=server
		self.remote = remote

		self.lay = QtGui.QGridLayout()
		self.lay.setSpacing(0)
		self.lay.setContentsMargins(0,0,0,0)
		self.viewer = picture.ViewerPicture(remote, server,  self)
		
		
		# Viewer has the middle cell
		self.lay.addWidget(self.viewer,2,2)
		
		self.setLayout(self.lay)
		
		# Proxy for viewer functions
		self.setSampleProcessor=self.viewer.setSampleProcessor
		self.setFrameProcessor=self.viewer.setFrameProcessor
	
	@property
	def processor(self):
		return self.viewer.processor
		
	def close(self):
		print 'ViewerControl.close'
		for ctrl in self.controls.itervalues():
			if ctrl is None: continue
			ctrl.close()
			self.lay.removeWidget(ctrl)
			ctrl.destroy()
		self.viewer.close()
		self.viewer=False
		
	def setControl(self, widget, position, tooltip='', inversion=0):
		"""Set a slider widget in the given position. Available positions: upper, bottom, left, right"""
		if not self.positions.has_key(position):
			print 'Impossible position requested',position
			return False
		if self.controls[position] is not None:
			print 'Position already has a control',position,self.controls[position]
			return False
		pos=self.positions[position]
		widget.label_widget.hide()
		if widget.slider:
			widget.slider.setToolTip(tooltip)
		# Rotate if in left/right position
		if position in ['left','right']:
			widget.setOrientation(QtCore.Qt.Vertical)
		self.lay.addWidget(widget,*pos)
		self.controls[position]=widget
		print 'ViewerControl.setControl',widget,position,pos
		
	def delControl(self,position):
		"""Removes a control widget placed in position"""
		wdg=self.controls[position]
		if wdg is None:
			print 'Impossible to remove the control widget',position
			return False
		self.lay.removeWidget(wdg)
		wdg.hide()
		wdg.close()
		wdg.destroy()
		self.controls[position]=None
		
	def delControls(self):
		"""Clears all control widgets."""
		for pos in self.positions.iterkeys():
			self.delControl(pos)
		
	

class CameraController(conf.Interface):
	"""An interface widget adding the "View Camera" button"""
	viewerDialog=False
	def __init__(self, server, remote, suffix='', parent=None):
		print 'CameraController.__init__', server, remote
		self.remote = remote
		self.server=server
		desc = self.remote.describe()
		conf.Interface.__init__(self, server, remote, prop_dict=desc, parent=parent)
		
		self.controls = []
		self.viewerDialog=False
		
		self.stream = QtGui.QPushButton(_("View camera"))
		
		print self.sectionsMap
		self.sectionsMap['Main'].lay.addWidget(self.stream)
		self.connect(self.stream, QtCore.SIGNAL('clicked()'), self.toggle_stream)
		
	def restoreFactory(self):
		print self.rpc.restoreFactory(self.idx)
		
	def toggle_stream(self, do=None):
		"""Activate/deactivate camera viewing"""
		print 'CameraController.toggle_stream', self.remote, self.server, self.viewerDialog
		if self.viewerDialog and self.viewerDialog.viewer:
			self.viewerDialog.close()
		self.viewerDialog=False
		self.viewerDialog = dialog.ViewerDialog(self.server,self.remote, parent=self)
		self.viewerDialog.show()
		self.viewerDialog.toggle_stream(True)
		self.connect(self, QtCore.SIGNAL('destroyed()'), self.viewerDialog.close)

	def close(self):
		if self.viewerDialog:
			self.viewerDialog.close()
