#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from traceback import format_exc
from .. import conf, widgets
from ..live import registry
from ..database import ProgressBar 
import measureinfo
from ..clientconf import confdb

class Controls(widgets.Linguist,QtGui.QToolBar):
	"""Start/stop toolbar"""
	mute=False
	motor=False
	isRunning=None
	"""Local running status"""
	paused=False
	"""Do not update actions"""
	started=QtCore.pyqtSignal()
	stopped=QtCore.pyqtSignal()
	stopped_nosave=QtCore.pyqtSignal()
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
		self.aobj.force_update=True
		self.aobj.register()
		self.name=self.remote['name'].lower()
		print 'Controls: ', self.name
		if self.name=='post':
			self.addAction('Machine Database', parent.showIDB)
			self.addAction('Test File', parent.openFile)
			self.addAction('Misura3 Database', parent.showDB3)
		print 'Controls.updateActions()'
		self.updateActions()
		print 'Controls end init'
		self.stopped.connect(self.hide_prog)
		self.stopped_nosave.connect(self.hide_prog)
		self.started.connect(self.hide_prog)
		self.connect(self, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
		self.connect(self.aobj, QtCore.SIGNAL('changed()'), self.updateActions)
		self.connect(self, QtCore.SIGNAL('warning(QString,QString)'), self.warning)
		
	@property
	def tasks(self):
		"""Shortcut to pending tasks dialog"""
		return registry.tasks

	def updateActions(self):
		"""Update status visualization and notify third-party changes"""
		if self.paused:
			return self.isRunning
		if self.parent().fixedDoc:
			return False
		# Always reconnect in case it is called in a different thread
		rem=self.server.copy()
		rem.connect()
		r=rem['isRunning']
		r=bool(r)
		self.stopAct.setEnabled(r)
		self.startAct.setEnabled(r^1)
		self.iniAct.setEnabled(r^1)
		if self.isRunning is not None and self.isRunning!=r:
			print 'Controls.updateActions',self.isRunning,r
			if r:
				msg='A new test was started'
				sig=self.started
			else:
				msg='Finished test'
				sig=self.stopped
			QtGui.QMessageBox.warning(self,msg,msg)
			sig.emit()
		# Locally remember remote status
		self.isRunning=r
# 		c=(1,0,0,1) if r else (0,1,0,1) 
# 		g=QtGui.QRadialGradient(0.5,0.5,0.99,0.5,0.5)
# 		g.setCoordinateMode(QtGui.QGradient.ObjectBoundingMode)
# 		g.setColorAt(0,QtGui.QColor.fromRgbF(0,0,0,0))
# 		g.setColorAt(1,QtGui.QColor.fromRgbF(*c))
# 		self.parent().area.setBackground(QtGui.QBrush(g))
		return r
		
	def enterEvent(self, ev):
		self.updateActions()
		return 
		
	def _async(self,method,*a,**k):
		"""Execute `method` in global thread pool, passing `*a`,`**k` arguments."""
		r=widgets.RunMethod(method,*a,**k)
		QtCore.QThreadPool.globalInstance().start(r)
		return True
	
	def _sync(self,method,*a,**k):
		"""Synchronously execute `method`,passing `*a`,`**k` arguments."""
		method(*a,**k)
		return True
	
		
	def warning(self,title,msg=False):
		"""Display a warning message box and update actions"""
		if not msg: msg=title
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
		self.paused=True
		rem=self.remote.copy()
		rem.connect()
		try:
			msg=rem.start_acquisition()
			self.started.emit()
		except:
			msg=format_exc()
			print msg
		self.paused=False
		self.started.emit()
		if not self.mute:
			self.emit(QtCore.SIGNAL('warning(QString,QString)'),
					'Start Acquisition', 
					'Result: '+msg)		

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
		self.isRunning=True
		self._async(self._start)
		self.show_prog("Starting new test")
		return True
		
	def _stop(self,mode):
		self.paused=True
		rem=self.remote.copy()
		rem.connect()
		try:	
			msg=rem.stop_acquisition(mode)
		except:	
			msg=format_exc()
		if mode:
			self.stopped.emit()
		else:
			self.stopped_nosave.emit()
		self.paused=False
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
			
		self.isRunning=False
		if btn==qm.Discard:
			self.stopped_nosave.emit()
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
		
class MotionControls(widgets.Linguist,QtGui.QToolBar):
	"""Motion toolbar"""
	mute=False
	motor=False
	#cycleNotSaved=False
	def __init__(self, remote, parent=None):
		widgets.Linguist.__init__(self,context='Acquisition')
		QtGui.QToolBar.__init__(self, parent)
		self.remote=remote
		self.server=remote.parent()
		
		if self.server.kiln['motorStatus']>=0:
			self.kmotor=widgets.build(self.server, self.server.kiln, self.server.kiln.gete('motorStatus'))
			self.kmotor.label_widget.label.setText('Furnace:')
			self.kmotor.lay.insertWidget(0,self.kmotor.label_widget)
			self.addWidget(self.kmotor)
		
		paths={}
		# Collect all focus paths
		for pic,win in self.parent().cameras.itervalues():
			print pic
			print pic.remote
			print pic.remote.encoder
			print pic.remote.encoder.focus
			
			obj=pic.remote.encoder.focus.roledev('motor')
			if not obj: continue
			paths[obj['fullpath']]=obj
		for obj in paths.itervalues():
			self.add_focus(obj)
			
	def add_focus(self,obj):
# 		slider=widgets.MotorSlider(self.server,obj,self.parent())
		slider=widgets.build(self.server, obj, obj.gete('goingTo'))
		slider.lay.insertWidget(0,slider.label_widget)
		slider.label_widget.label.setText('    Focus:')
		self.addWidget(slider)
		
			