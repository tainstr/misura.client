#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Client-Server Synchronization"""

from misura.canon.logger import Log as logging
from time import sleep, time
from cPickle import loads
import threading
from traceback import format_exc
from misura.canon import option
from misura.canon.csutil import lockme, profile
from misura.client.network import manager as net
from misura.client import _
from PyQt4 import QtGui, QtCore
from tasks import Tasks
		
		
#TODO: we should NEVER reference widgets here, just KIDs (except pending tasks)
class KidRegistry(QtCore.QThread):
	"""Configuration keys registry"""
	proxy=False
	stream=False
	interval=1
	"""Update interval (s)"""
	tasks=False
	"""Local tasks dialog"""
	taskswg = False
	system_kids=set(['/isRunning'])
	"""Set of forced update system kids. These are always updated."""
	#TODO: add queued_kids, a way to asynchronous one-time-update 
	system_kid_changed=QtCore.pyqtSignal(str)
	"""Signal emitted when a system kid changes."""
	conn_error=QtCore.pyqtSignal(int)
	"""Signal emitted when connection errors counter changes."""
	connection_error_count=0
	max_connection_errors=0
	def __init__(self):
		QtCore.QThread.__init__(self)
		self.rid={}
		"""Dict KID:[awg0,awg1,...]"""
		self.times={}
		"""Dict KID: last update server time"""
		self.values={}
		"""Dict KID: value"""
		self.obj=False
		"""MisuraProxy"""
		self.curves={}
		"""Dict kid:curve"""
		self.ktime=0
		"""Last recorded kid"""
		self._lock=threading.Lock()
		self.__call__=self.register
		self.log_buf=[]
		self.log_time=0
		self.updatingCurves=False
		self.doc=False
		self.manager=False
			
	@lockme
	def set_manager(self,man=None):
		old_stream=self.stream
		self.stream=False
		if self.isRunning():
			self.wait(1)
		self.manager=man
		logging.debug('KidRegistry.set_manager %s',man)
		self.taskswg=Tasks()
		self.connect(self, QtCore.SIGNAL('set_server(PyQt_PyObject)'), self.taskswg.set_server)
		if man is not None:
			if man.remote:
				logging.debug('%s %s', 'KidRegistry.set_manager with remote', man.remote)
				self.emit(QtCore.SIGNAL('set_server(PyQt_PyObject)'), man.remote)
			else:
				logging.debug('%s %s', 'KidRegistry.set_manager without remote', man.remote)
		else:
			logging.debug('%s %s', 'KidRegistry.set_manager set to None', man)
		if old_stream:
			self.stream=True
			self.start()
	
	@property
	def progress(self):
		return self.taskswg.progress

	@property
	def tasks(self):
		"""Return local tasks widget"""
		if not self.taskswg:
			return False
		return self.taskswg.tasks

	@lockme
	def set_doc(self,doc=False):
		"""Install new document `doc`"""
		if not doc and self.doc:
			self.dicconnect(self,QtCore.SIGNAL('update()'),self.doc.update)
			self.lastdoc=False
			logging.debug('%s', 'KidRegistry.set_doc CLEARED')
		self.doc=doc
		if doc:
			self.connect(self,QtCore.SIGNAL('update()'),self.doc.update)

#FIXME: should be locked. It was unlocked for performance, but SHOULD BE LOCKED
#	@lockme
	def register(self, w):
		"""Register Active object `w`"""
		if w.type=='Button':
			return False
		if not w.prop:
			logging.debug('No property for active widget. Impossible to register')
			return False
		kid=w.prop['kid']
		# Add to the dictionary
		if not self.rid.has_key(kid):
			self.rid[kid]=[]
			self.times[kid]=0
		if w in self.rid[kid]:
			return kid
		self.rid[kid].append(w)
		return kid
	
#FIXME: should be locked. It was unlocked for performance, but SHOULD BE LOCKED
#	@lockme
	def unregister(self, widget):
		"""Removes a widget from the registry."""
		if not widget.prop:
			return 
		key_id = widget.prop['kid']
		if self.rid.has_key(key_id):
			if widget in self.rid[key_id]:
				self.rid[key_id].remove(widget)
			del widget
			if len(self.rid[key_id]) == 0:
				del self.rid[key_id]
				if self.times.has_key(key_id):
					del self.times[key_id]
			
	@lockme
	def clear(self):
		"""Removes all registered objects."""
		self.rid={}
		self.times={}
	
	
	def _build_request(self):
		"""Build a request for mapdate() based on valid and visible registered widgets."""
		request=[]
		# Force progress update
		cur = self.obj.get('progress')
		if self.progress.progress:
			self.progress.progress.emit(QtCore.SIGNAL('selfchanged'), cur)
		for kid,ws in self.rid.items():
			t= self.times.get(kid, 0)
			do=False
			# Search for valid entry and forced update
			for w in ws[:]:
				if w==self.progress.progress: 
					continue
				do=1
				if w.force_update:
					t=-1	# force mapdate to update this value
				break
			# Just progresses
			if not do:
				continue
			# Aggregate request
			request.append((kid,t))
		# Force special requests:
		for kid in self.system_kids:
			request.append((kid,self.times.get(kid, 0)))
		return request
		
	@lockme
	def update_all(self):
		"""Update registered objects."""
		updated=[]
		# Prepare request list 
		request = self._build_request()
		# Call remote mapdate()
		r = self.obj.mapdate(request)
		if not r or r is None:
			logging.debug('%s', 'KidRegistry.update_all SKIPPING')
			return False
		idx, reply = r
		# Decode the reply
		nt = self.obj.time()
		for i, j in enumerate(idx):
			nval=reply[i]
			kid, ot=request[j]
			self.times[kid]=nt
			# Apply the new value
			ws = self.rid.get(kid, [])
			# forget all widgets for this kid
			self.rid[kid]=[] 
			self.values[kid]=nval
			for w in ws:
				try:
					w.emit(QtCore.SIGNAL('selfchanged'), nval)
					updated.append(w)
				except:
					continue
			if kid=='/progress' and self.progress:
				self.progress.emit(QtCore.SIGNAL('selfchanged'), nval)
			# Notify system kid changes
			if kid in self.system_kids:
				self.system_kid_changed.emit(kid)
		return updated
		
	def force_redraw(self):
		for kid,ws in self.rid.items():
			for w in ws:
				w.emit(QtCore.SIGNAL('changed()'))
	
	@lockme
	def updateLog(self):
		r=self.obj.get_log(self.log_time)
		if r is None:
			return False
		ltime, buf=r
		if ltime<=self.log_time: return True
		self.log_time=ltime
		self.log_buf+=buf
		self.emit(QtCore.SIGNAL('log()'))
		return True

	def setInterval(self, ms):
		"""Change update interval"""
		self.interval=ms*.001
		
	def control_loop(self):
		"""Called while the registry is running."""
		self.emit(QtCore.SIGNAL('cycle()'))
		if self.obj is False:
			if not self.manager:
				logging.debug('%s', 'KidRegistry.control_loop: No manager registered.')
				return True
			if not self.manager.remote:
# 				print 'KidRegistry.control_loop: no remote manager'
				return True
			self.obj=self.manager.remote.copy()
			self.obj.connect()
			self.emit(QtCore.SIGNAL('set_server(PyQt_PyObject)'), self.obj)
		if not net.connected:
			logging.debug('%s', 'KidRegistry.control_loop: Not connected')
			return True
		self.obj._reg=self
		if self.doc and (self.doc is not self.lastdoc):
			if self.doc.proxy:
				self.proxy=self.doc.proxy.copy()
				self.proxy.connect()
				self.lastdoc=self.doc
#		if self.proxy: 
#			self.proxy.connect()
		# If a doc is registered and remote is running acquisition, update the document
		if self.obj['isRunning']:
			if self.doc:
				self.doc.update(proxy=self.proxy)
		else:
			self.taskswg.sync.loop(self.obj)
		r=True
		if not self.updateLog():
			r=False
		if self.update_all() is False:
			r=False
		return r

	def run(self):
		"""Execution entry for the registry thread.
		Will call control_loop() until self.stream is True."""
		logging.debug('%s %s', 'Starting registry in new thread', len(self.rid))
		self.setPriority(QtCore.QThread.IdlePriority)
		t0=time()
#		self.obj=False
		self.stream=True
		self.lastdoc=False
# 		if self.taskswg:
# 			self.taskswg.sync.moveToThread(self)
		while self.stream:
			# Sleep only if loops are shorter than interval
# 			print 'KidRegistry.run', len(self.rid)
			t=time()
			d=self.interval-(t-t0)
			if d>0:	sleep(d)
			t0=t
			try:
				# Everything good
				if self.control_loop():
					self.connection_error(count=-1)
				else:
					self.connection_error()
			except:
				logging.debug(format_exc())
				sleep(1)
				self.connection_error()
		logging.debug('%s %s', 'KidRegistry.run END', self.stream)

	
	def toggle_run(self, auto=None):
		"""Start/stop KID reading thread"""
		if auto==None: 
			auto=self.stream^1
		logging.debug('%s %s', 'KidRegistry.toggle_run', auto)
		if auto==True:
			self.stream=True
			if not self.isRunning():
				self.start()
		elif auto==False:
			self.stream=False
			if self.isRunning():
				self.wait(1)
	
	def connection_error(self,count=1):
		"""Increase or decrease connection error counter"""
		old=self.connection_error_count
		if count>0:
			self.connection_error_count+=count
		else:
			self.connection_error_count/=2
			self.connection_error_count-=1
		print 'CONN ERRORS',old,self.connection_error_count, self.max_connection_errors
		# Reset
		if self.connection_error_count<=0:
			self.connection_error_count=0
			self.max_connection_errors=0
			self.tasks.done('Connection errors')
			return
		# Detect new error sequence
		if self.connection_error_count > self.max_connection_errors:
			self.max_connection_errors=self.connection_error_count
			self.tasks.jobs(self.connection_error_count,'Connection errors')
		# Notify changes
		if old!=self.connection_error_count:
			self.tasks.job(1+self.max_connection_errors-self.connection_error_count,'Connection errors')
			self.conn_error.emit(self.connection_error_count)

			
		

