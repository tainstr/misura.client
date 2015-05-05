#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Pending tasks feedback"""

from misura.canon.csutil import lockme, profile
from .. import _
import functools
from PyQt4 import QtGui, QtCore

class PendingTasks(QtGui.QWidget):
	server=False
	progress=False
	ch=QtCore.pyqtSignal()
	def __init__(self):
		QtGui.QWidget.__init__(self)
		self.lay=QtGui.QVBoxLayout(self)
		self.setLayout(self.lay)
		self.setWindowTitle('Remote Pending Tasks')
		
	def __len__(self):
		if self.progress is False:
			return 0
		r=len(self.progress.prog)
		return r
		
	def set_server(self, server):
		if not server:
			return False
		self.server=server.copy()
		self.server.connect()
		server=self.server
		# Clean the layout
		if self.progress:
			try:
				self.progress.hide()
			finally:
				self.progress=False
		from ..widgets import RoleProgress
		prop=server.gete('progress')
		self.progress=RoleProgress(server, server, prop, parent=self )
		self.progress.force_update=True
		self.progress.label_widget.hide()
		self.lay.addWidget(self.progress)
		self.connect(self.progress, QtCore.SIGNAL('changed()'), self.update)
		self.connect(self.progress, QtCore.SIGNAL('selfchanged'), self.update)
		self.update()
		
	def update(self, *a, **k):
		if len(self)==0:
			self.hide()
		else:
			self.show()
		self.ch.emit()
			
		
			

class LocalTasks(QtGui.QWidget):
	"""Global server 'progress' option widget. This is a RoleIO pointing to the real 'Progress'-type option being performed"""
	ch=QtCore.pyqtSignal()
	sig_done=QtCore.pyqtSignal(str)
	sig_done0=QtCore.pyqtSignal()
	def __init__(self):
		QtGui.QWidget.__init__(self)
		self.lay=QtGui.QHBoxLayout()
		self.setLayout(self.lay)
		self.setWindowTitle(_('Local Operations in Progress'))
		# Base widget
		self.bw=QtGui.QWidget(parent=self)
		self.blay=QtGui.QVBoxLayout()
		self.bw.setLayout(self.blay)
		self.log=QtGui.QTextEdit(parent=self)
		self.log.setReadOnly(True)
		self.log.setLineWrapMode(self.log.NoWrap)
		self.log.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
		self.log.hide()
		self.more=QtGui.QPushButton(_('Log'), parent=self)
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
		
		self.connect(self,QtCore.SIGNAL('jobs(int)'),self._jobs)
		self.connect(self,QtCore.SIGNAL('jobs(int,QString)'),self._jobs)
		
		self.connect(self,QtCore.SIGNAL('job(int,QString,QString)'),self._job)
		self.connect(self,QtCore.SIGNAL('job(int,QString)'),self._job)
		self.connect(self,QtCore.SIGNAL('job(int)'),self._job)
		
		self.sig_done.connect(self._done)
		self.sig_done0.connect(self._done)
		print 'LocalTasks initialized'
		
	def __len__(self):
		return len(self.prog)
		
	def toggle_log(self):
		if self.log.isVisible():
			self.log.hide()
			self.mlay.removeWidget(self.log)
			return 
		self.log.show()
		
	def msg(self,msg):
		txt=self.log.toPlainText()
		txt+=msg+'\n'
		self.log.setPlainText(txt)
				
	def _jobs(self,tot,pid='Operation'):
		"""Initialize a new progress bar for job `pid` having total steps `tot`."""
		wg=self.prog.get(pid)
		if wg:
			wg.pb.setRange(0,tot)
			if not self.isVisible():
				self.ch.emit()
				self.show()
			return
		wg=QtGui.QWidget()
		pb=QtGui.QProgressBar(self)
		pb.setRange(0,tot)
		lbl=QtGui.QLabel(pid)
		btn=QtGui.QPushButton('X')
		wg._func_close=functools.partial(self.done,pid)
		btn.connect(btn,QtCore.SIGNAL('clicked()'),wg._func_close)
		
		lay=QtGui.QHBoxLayout()
		lay.addWidget(lbl)
		lay.addWidget(pb)
		lay.addWidget(btn)
		wg.setLayout(lay)
		wg.pb=pb
		self.mlay.addWidget(wg)
		self.prog[pid]=wg
		if not self.isVisible():
			self.show()
			self.ch.emit()
			
	def jobs(self,tot,pid='Operation'):
		"""Thread-safe call for _jobs()"""
		self.emit(QtCore.SIGNAL('jobs(int,QString)'),tot,pid)
		
	
	def _job(self,step,pid='Operation',label=''):
		"""Progress job `pid` to `step`, and display `label`. A negative step causes the bar to progress by 1."""
		wg=self.prog.get(pid,False)
		if not wg:
			print 'LocalTasks.jog: no job defined!',pid
			return
		if step<0:
			step=wg.pb.value()+1
		wg.pb.setValue(step)
		if label!='':
			self.msg(pid+': '+label)
		if step==wg.pb.maximum() and step!=0:
			self._done(pid)
		QtGui.qApp.processEvents()
		
	def job(self,step,pid='Operation',label=''):
		"""Thread-safe call for _job()"""
		self.emit(QtCore.SIGNAL('job(int,QString,QString)'),
				step,pid,label)		
	
	def _done(self,pid='Operation'):
		"""Complete job `pid`"""
		wg=self.prog.get(pid,False)
		if not wg: 
			print 'LocalTasks.done: no pid',pid
			return False
		wg.hide()
		del self.prog[pid]
		self.mlay.removeWidget(wg)
		del wg
		self.msg('Completed task: '+str(pid))
		print 'LocalTasks.done',self.prog
		self.ch.emit()
		return True
	
	def done(self,pid='Operation'):
		"""Thread-safe call for _done()"""
		self.sig_done.emit(pid)
		
class Tasks(QtGui.QWidget):
	def __init__(self):
		QtGui.QWidget.__init__(self)
		self.lay=QtGui.QVBoxLayout()
		self.setLayout(self.lay)
		self.setWindowTitle(_('Pending Operations'))
		self.tasks=LocalTasks()
		self.lay.addWidget(self.tasks)
		self.progress=PendingTasks()
		self.lay.addWidget(self.progress)
		
		self.tasks.ch.connect(self.hide_show)
		self.progress.ch.connect(self.hide_show)
		
	def hide_show(self):
		if len(self.tasks)+len(self.progress):
			self.show()
		else:
			self.hide()
		
		
		
		
