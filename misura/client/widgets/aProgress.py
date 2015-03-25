#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Progress bar"""
import sys
from PyQt4 import QtCore,QtGui
from traceback import print_exc
from misura.client.parameters import MAX,MIN
from misura.client.widgets.active import ActiveWidget
import math


class aProgress(ActiveWidget):
	def __init__(self, server, remObj, prop, parent=None):
		ActiveWidget.__init__(self, server, remObj, prop, parent)
		m=self.prop.get('max', 1)
		# If max/min are defined, create the slider widget
		self.bar=QtGui.QProgressBar(self)
		self.bar.setMinimum(0)
		self.update(get=False)
		self.lay.addWidget(self.bar)
		
	def adapt(self, val):
		return int(val)
		
	def update(self, get=True):
		# Update minimum and maximum
		if get:
			self.prop=self.remObj.gete(self.handle)
		self.current=self.adapt2gui(self.prop['current'])
		m=self.adapt2gui( self.prop.get('max', 1))
		if m!=self.bar.maximum():
			self.bar.setMaximum(m)
		self.bar.setValue(self.current)
		if	self.current==0:
			self.bar.setEnabled(False)
			self.bar.reset()
		else:
			self.bar.setEnabled(True)
			

class RoleProgress(ActiveWidget):
	"""Global server 'progress' option widget. This is a RoleIO pointing to the real 'Progress'-type option being performed"""
	def __init__(self, server, remObj, prop, parent=None,slider_class=QtGui.QSlider):
		ActiveWidget.__init__(self, server, remObj, prop, parent)
		self.setWindowTitle(self.mtr('Remote Operation in Progress'))
		# Base widget
		self.bw=QtGui.QWidget(parent=self)
		self.blay=QtGui.QVBoxLayout()
		self.bw.setLayout(self.blay)
		self.log=QtGui.QTextEdit(parent=self)
		self.log.setReadOnly(True)
		self.log.setLineWrapMode(self.log.NoWrap)
		self.log.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
		self.log.hide()
		self.more=QtGui.QPushButton(self.mtr('Log'), parent=self)
		self.connect(self.more, QtCore.SIGNAL('clicked()'), self.toggle_log)
		

		# Progress bars widget
		self.mw=QtGui.QWidget(parent=self)
		self.mlay=QtGui.QVBoxLayout()
		self.mw.setLayout(self.mlay)
		# Populate the base widget with progress widget, more button, log window
		self.blay.addWidget(self.mw)
		self.blay.addWidget(self.more)
		self.blay.addWidget(self.log)	
		
		self.lay.addWidget(self.bw)
		
		self.prog={}
		self.update()
		self.label_widget.label.setText('Remote operations')
		
	def toggle_log(self):
		if self.log.isVisible():
			self.log.hide()
			self.mlay.removeWidget(self.log)
			return 
		self.log.show()
		
	def update(self):
		# Check if there is something to update
		vis=set(self.prog.keys()) # Set of visible progress bars
		cur=set(self.current) # Set of remote pending tasks
		# Remove no longer active tasks
		for k in vis-cur:
			p=self.prog[k]
			txt=self.log.toPlainText()
			txt+='Done: '+p.label_widget.label.text()+'\n'
			self.log.setPlainText(txt)
			p.hide()
			self.mlay.removeWidget(p)
			p.close()
			del self.prog[k]
		# Insert new tasks
		add=cur-vis
		for k in add:
			e=k.split('/')[1:]
			opt=e.pop(-1)
			obj=self.server.toPath(e)
			prop=obj.gete(opt)
			if prop is None: 
				continue
			p=aProgress(self.server, obj, prop, parent=self.mw)
			txt=obj['name'].capitalize()+': '+p.label_widget.label.text()
			p.label_widget.label.setText(txt)
			p.lay.insertWidget(0, p.label_widget) # show label before pbar
			self.mlay.addWidget(p)
			# Remember progress
			self.prog[k]=p
			# Log line
			txt=self.log.toPlainText()+'Started: '+txt+'\n'
			self.log.setPlainText(txt)
			
#		# Update old bars
#		for k in set(self.prog.keys())-add:
#			self.prog[k].update()
			

	
