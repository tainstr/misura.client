#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Client-Server Synchronization"""

from misura.canon.logger import Log as logging
from time import sleep, time
from cPickle import loads
import threading
from traceback import print_exc
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
	progress=False
	"""Remote progress dialog"""
	tasks=False
	"""Local tasks dialog"""
	taskswg = False
	system_kids=set(['/isRunning'])
	"""Set of forced update system kids. These are always updated."""
	#TODO: add queued_kids, a way to asynchronous one-time-update 
	system_kid_changed=QtCore.pyqtSignal(str)
	"""Signal emitted when a system kid changes."""
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
		self.manager=man
		self.taskswg=Tasks()
		self.connect(self, QtCore.SIGNAL('set_server(PyQt_PyObject)'), self.taskswg.progress.set_server)
		if man is not None:
			if man.remote:
				logging.debug('%s %s', 'KidRegistry.set_manager with remote', man.remote)
				self.emit(QtCore.SIGNAL('set_server(PyQt_PyObject)'), man.remote)
			else:
				logging.debug('%s %s', 'KidRegistry.set_manager without remote', man.remote)
		else:
			logging.debug('%s %s', 'KidRegistry.set_manager set to None', man)
	
	@property
	def progress(self):
		return self.taskswg.progress

	@property
	def tasks(self):
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

#	@lockme
	def register(self, w):
		"""Register Active object `w`"""
		if w.type=='Button':
			logging.debug('%s', 'It is not possible to register "Button" widgets.')
			return False
		kid=w.prop['kid']
		# Add to the dictionary
		if not self.rid.has_key(kid):
			self.rid[kid]=[]
			self.times[kid]=0
		if w in self.rid[kid]:
			logging.debug('%s %s %s', 'Already registered', kid, w)
			return kid
		self.rid[kid].append(w)
		return kid
	
#	@lockme
	def unregister(self, w):
		"""Removes a widget from the registry."""
		kid=w.prop['kid']
		if self.rid.has_key(kid):
			if w in self.rid[kid]:
				self.rid[kid].remove(w)
			del w
			if len(self.rid[kid])==0:
				del self.rid[kid]
		if self.times.has_key(kid):
			del self.times[kid]
			
	@lockme
	def clear(self):
		"""Removes all registered objects."""
		return 
# 		self.rid={}
# 		self.times={}
	
	
	def _build_request(self):
		"""Build a request for mapdate() based on valid and visible registered widgets."""
		request=[]
		# Force progress update
		cur=self.obj.get('progress')
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
		request=self._build_request()
		# Call remote mapdate()
		r=self.obj.mapdate(request)
		if not r or r is None:
			logging.debug('%s', 'KidRegistry.update_all SKIPPING')
			return []
		idx, reply=r
		# Decode the reply
		nt=self.obj.time()
		for i, j in enumerate(idx):
			nval=reply[i]
			kid, ot=request[j]
			self.times[kid]=nt
			# Apply the new value
			ws=self.rid.get(kid, [])
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
# 		print 'Registry.update_all', len(updated)
		return updated
		
	def force_redraw(self):
		for kid,ws in self.rid.items():
			for w in ws:
				w.emit(QtCore.SIGNAL('changed()'))
	
	@lockme
	def updateLog(self):
		ltime, buf=self.obj.get_log(self.log_time)
		if ltime<=self.log_time: return
		self.log_time=ltime
		self.log_buf+=buf
		self.emit(QtCore.SIGNAL('log()'))

	def setInterval(self, ms):
		"""Change update interval"""
		self.interval=ms*.001
		
	def control_loop(self):
		"""Called while the registry is running."""
		self.emit(QtCore.SIGNAL('cycle()'))
		if self.obj is False:
			if not self.manager:
				logging.debug('%s', 'KidRegistry.control_loop: No manager registered.')
				return False
			if not self.manager.remote:
# 				print 'KidRegistry.control_loop: no remote manager'
				return False
			self.obj=self.manager.remote.copy()
			self.obj.connect()
			self.emit(QtCore.SIGNAL('set_server(PyQt_PyObject)'), self.obj)
		if not net.connected:
			logging.debug('%s', 'KidRegistry.control_loop: Not connected')
			return False
		if self.doc and (self.doc is not self.lastdoc):
			if self.doc.proxy:
				self.proxy=self.doc.proxy.copy()
				self.proxy.connect()
				self.lastdoc=self.doc
#		if self.proxy: 
#			self.proxy.connect()
		# If a doc is registered and remote is running acquisition, update the document
		if self.doc and self.obj['isRunning']:
# 			self.emit(QtCore.SIGNAL('update()'))
			self.doc.update(proxy=self.proxy)
		self.updateLog()
		self.update_all()
		return True

	def run(self):
		"""Execution entry for the registry thread.
		Will call control_loop() until self.stream is True."""
		logging.debug('%s %s', 'Starting registry in new thread', len(self.rid))
		self.setPriority(QtCore.QThread.IdlePriority)
		t0=time()
#		self.obj=False
		self.stream=True
		self.lastdoc=False
		while self.stream:
			# Sleep only if loops are shorter than interval
# 			print 'KidRegistry.run', len(self.rid)
			t=time()
			d=self.interval-(t-t0)
			if d>0:	sleep(d)
			t0=t
			try:
				self.control_loop()
			except:
				logging.debug('%s', print_exc())
				sleep(1)
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
#			if self.isRunning():
#				self.quit()

#registry=KidRegistry()
