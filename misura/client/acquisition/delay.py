#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Delayed test start dialog"""
from time import time
import sys
from .. import widgets
from PyQt4 import QtGui, QtCore


class DelayedStart(QtGui.QDialog):
	def __init__(self,server):
		QtGui.QDialog.__init__(self)
		self.server=server
		self.ins=getattr(server,server['lastInstrument'])
		
		self.setWindowTitle('Delayed Test Start')
		self.lay=QtGui.QVBoxLayout()
		self.eng=widgets.aBoolean(server,server,server.gete('delayStart'))
		self.wg=widgets.aDelay(server,server,server.gete('delay'))
		h=time()+3600
		if self.wg.current<h and not self.eng.current:
			self.wg.set(h)
		self.eng.lay.insertWidget(0,self.eng.label_widget)
		self.lay.addWidget(self.eng)
		self.wg.lay.insertWidget(0,self.wg.label_widget)
		self.lay.addWidget(self.wg)
		
		self.run=QtGui.QLabel('Target instrument: '+server['lastInstrument'].capitalize())
		self.lay.addWidget(self.run)
		
		self.eta=QtGui.QLabel('Remaining time: --:--:--')
		self.lay.addWidget(self.eta)
		
		self.op=QtGui.QLabel('Operator: unknown')
		self.lay.addWidget(self.op)
		
		self.quit=QtGui.QPushButton("Save and exit",parent=self)
		self.connect(self.quit,QtCore.SIGNAL('clicked()'),self.save_exit)
		self.lay.addWidget(self.quit)
		self.abrt=QtGui.QPushButton("Abort delayed start",parent=self)
		self.connect(self.abrt,QtCore.SIGNAL('clicked()'),self.reject)
		self.lay.addWidget(self.abrt)
		
		
		self.setLayout(self.lay)
		self.connect(self,QtCore.SIGNAL('finished(int)'),self.unset)
		self.setWindowModality(QtCore.Qt.WindowModal)
		
		self.timer=QtCore.QTimer(self)
		self.timer.connect(self.timer, QtCore.SIGNAL('timeout()'), self.update)
		self.timer.start(1000)
		

	def unset(self,*a):
		"""Disable delayed start on exit"""
		self.wg.server['delayStart']=False
	
	def save_exit(self):
		"""Completely close the client"""
		if self.eng.current:
			btn=QtGui.QMessageBox.warning(self,"Delayed start is active","You are exiting from the client application, \nbut a delayed start will remain active on the instrument.")
			sys.exit(0)
		self.done(0)
		
	def update(self):
		dt='--:--:--'
		self.ins=getattr(self.server,self.server['lastInstrument'])
		if self.eng.current:
			dt=self.wg.current+self.wg.delta-time()
			dt=QtCore.QTime().addSecs(dt)
			dt=dt.toString('hh:mm:ss')
			self.wg.twg.setReadOnly(True)
			self.quit.setEnabled(True)
		else:
			self.wg.twg.setReadOnly(False)
			self.quit.setEnabled(False)
		self.eta.setText('Remaining time: {}'.format(dt))
		self.op.setText('Operator: '+self.ins.measure['operator'])
		
		
		
		