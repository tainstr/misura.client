#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from traceback import format_exc
from .. import conf, widgets
from ..live import registry
from ..database import ProgressBar 
import measureinfo

class Controls(widgets.Linguist,QtGui.QToolBar):
	"""Start/stop toolbar"""
	mute=False
	motor=False
	#cycleNotSaved=False
	def __init__(self, remote, parent=None):
		widgets.Linguist.__init__(self,context='Acquisition')
		QtGui.QToolBar.__init__(self, parent)
		self.remote=remote
		print 'Controls: init'
		self.server=remote.parent()
		self.iniAct=self.addAction('New', self.new)
		self.startAct=self.addAction('Start', self.start)
		self.stopAct=self.addAction('Stop', self.stop)
		print 'Controls: aobj'
		self.aobj=widgets.ActiveObject(self.server, self.server, self.server.gete('isRunning'), self)
		self.aobj.isVisible=self.isVisible
		self.aobj.force_update=True
		self.name=self.remote['name'].lower()
		print 'Controls: ', self.name
		if self.name=='post':
			self.addAction('Machine Database', parent.showIDB)
			self.addAction('Test File', parent.openFile)
			self.addAction('Misura3 Database', parent.showDB3)
		if self.server.kiln['motorStatus']>=0:
			print 'Controls: Adding motorStatus'
			self.motor=widgets.build(self.server, self.server.kiln, self.server.kiln.gete('motorStatus'))
			self.addWidget(self.motor)
		print 'Controls.updateActions()'
		self.updateActions()
		print 'Controls end init'
		self.connect(self,QtCore.SIGNAL('stopped()'),self.hide_prog)
		self.connect(self,QtCore.SIGNAL('started()'),self.hide_prog)
		self.connect(self, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
		self.connect(self.aobj, QtCore.SIGNAL('changed()'), self.updateActions)
		self.connect(self, QtCore.SIGNAL('warning(QString,QString)'), self.warning)
		
	@property
	def tasks(self):
		return registry.tasks

	def updateActions(self):
		r=self.server['isRunning']
		print 'updateActions',r
		r=bool(r)
		self.stopAct.setEnabled(r)
		self.startAct.setEnabled(r^1)
		self.iniAct.setEnabled(r^1)
		if self.motor is not False:
			self.motor.update()
		return r
		
	def enterEvent(self, ev):
		self.updateActions()
		return 
		
	def _async(self,method,*a,**k):
		r=widgets.RunMethod(method,*a,**k)
		QtCore.QThreadPool.globalInstance().start(r)
		return True
	
	def __async(self,method,*a,**k):
		"""SYNC"""
		method(*a,**k)
		return True
	
		
	def warning(self,title,msg):
		QtGui.QMessageBox.warning(self, title, msg)
		self.updateActions()
		
	_prog=False
	@property
	def prog(self):
		if not self._prog:
			self._prog=ProgressBar()
		return self._prog
	
	msg=''
	def show_prog(self,msg):
		self.msg=msg
		self.tasks.jobs(0,msg)
		self.tasks.setFocus()
		
	def hide_prog(self):
		self.tasks.done(self.msg)
		
	def _start(self):
		# Renovate the connection: we are in a sep thread!
		rem=self.remote.copy()
		rem.connect()
		try:
			msg=rem.start_acquisition()
			self.emit(QtCore.SIGNAL('started()'))
		except:
			msg=format_exc()
			print msg
		if not self.mute:
			self.emit(QtCore.SIGNAL('warning(QString,QString)'),
					'Start Acquisition', 
					'Result: '+msg)
		self.emit(QtCore.SIGNAL('started()'))	

	def start(self):
		self.mainWin=self.parent()
		self.mDock=self.mainWin.measureDock
		self.measureTab=self.mDock.widget()
		self.measureTab.checkCurve()
		if not self.validate():
			return False
		if self.updateActions():
			self.warning('Already running', 'Acquisition is already running. Nothing to do.')
			return False
		self._async(self._start)
		self.show_prog("Starting new test")
		return True
		
	def _stop(self,mode):
		rem=self.remote.copy()
		rem.connect()
		try:	
			msg=rem.stop_acquisition(mode)
		except:	
			msg=format_exc()
		self.emit(QtCore.SIGNAL('stopped()'))
		if self.mute:
			return
		
		if not mode:
			self.emit(QtCore.SIGNAL('warning(QString,QString)'),
					'Measurement data discarded!', \
					'Current measurement was stopped and its data has been deleted. \n'+msg)
		else:
			self.emit(QtCore.SIGNAL('warning(QString,QString)'),
					'Measurement stopped and saved', \
					'Current measurement was stopped and its data has been saved. \n'+msg)
		
	def stop(self):
		if not self.updateActions():
			self.warning('Already stopped', 'No acquisition is running. Nothing to do.')
			return
		qm=QtGui.QMessageBox
		if not self.mute:
			btn=qm.question(self, 'Save the test',  'Do you want to save this measurement?', \
			                               qm.Save|qm.Discard|qm.Abort, qm.Save)
			if btn==qm.Abort:
				qm.information(self, 'Nothing done.',  'Action aborted. The measurement maybe still running.')
				return False
		else:
			btn=qm.Discard
		
		if btn==qm.Discard:
			self.emit(QtCore.SIGNAL('stopped_nosave()'))
			self._async(self._stop,False)
		else:
			self._async(self._stop,True)
		self.show_prog("Stopping current test")
		
	def new(self):
		self.parent().init_instrument()

	def validate(self):
		"""Show a confirmation dialog immediately before starting a new test"""
		#TODO: generalize
		if self.remote['name'] in ['horizontal','vertical','flex']:
			val,st=QtGui.QInputDialog.getDouble(self,self.mtr("Confirm initial sample dimension"),
											self.mtr("Initial dimension (micron)"),
											self.remote.sample0['initialDimension'])
			if not st:
				return False
			self.remote.sample0['initialDimension']=val
		return True
		
		
		
		
		
