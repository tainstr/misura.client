#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Interfaces for local and remote file access"""
import logging
from PyQt4 import QtCore
import exceptions
from time import sleep

MAX=10**5
MIN=-10**5


class FilePlayer(QtCore.QThread):
	"""Plays a file emitting signals which are compatible with ViewerPicture"""
	idx=0
	stream=0
	sleep=0.1
	doc=False
	def __init__(self,parent=None):
		QtCore.QThread.__init__(self, parent)
		self.opt=set([])
		
	def set_doc(self,doc):
		if self.isRunning():
			logging.debug('%s', 'stopping')
			self.stream = 0
			self.terminate()
		if self.doc:
			for dec in doc.decoders.itervalues():
				logging.debug('%s %s', 'stopping decoder', dec.datapath)
				doc.terminate()
		self.params={}
		self.samples=[]
		self.opt=set([])
		self.doc=doc
		
	def close(self):
		for d in self.doc.decoders:
			d.close()
		
	def __getitem__(self,var):
		"""Fake the remote server 'isRunning' option"""
		if var=='isRunning':
			return self.isRunning()
		elif var=='frame_number':
			return self.idx
		raise exceptions.KeyError(var)
	
	def start_acquisition(self,*a):
		self.stream=1
		self.start()
		return 'Test replay started'
	
	def stop_acquisition(self,*a):
		logging.debug('%s', 'STOP ACQUISITION')
		self.stream=0
		self.terminate()
			
	def set_samples(self,*a,**b):
		pass
	
	def outIdx(self,idx):
		logging.debug('%s %s', 'outIdx', idx)
		self.idx=idx
		
	def set_idx(self,idx=-1):
		logging.debug('%s %s', 'FilePlay.set_idx', idx)
		if not self.doc:
			logging.debug('%s', 'NO DOC')
			return
		if idx<0: idx=self.idx
		img=True
		for dec in self.doc.decoders.itervalues():
			dimg=dec.get(idx)
			if not dimg:
				logging.debug('%s %s %s', 'error getting data from', dec.datapath, idx)
			img=img and dec.get(idx)
		if not img:
			logging.debug('%s', 'Could not get some data')
			return 
		self.idx=idx
		
		# EMIT ROI INFO
		# Get ROI coords for each sample from the current row
		meta=self.doc.get_row(idx)
		samples={}
		idxes={}
		for col,val in meta.iteritems():
			col=col.split('_')
			if len(col)!=2: continue
			smp=col[0]
			if not smp.startswith('smp'): continue
			try:
				sidx=int(smp[3:])
			except exceptions.ValueError:
				continue
			var=col[1]
			# Variable name not registered as emit-able
			if var not in self.opt: continue
			if not samples.has_key(smp):
				samples[smp]={}
			samples[smp][var]=val
			idxes[smp]=sidx
			
		# Add profile data
		if 'profile' in self.opt:
			for smp in samples.keys():
				prf=self.doc.decoders['/dat/'+smp].get(idx)
				if not prf: continue
				samples[smp]['profile']=prf
				
		# Emit roiUpdated for each sample
		for smp,multiget in samples.iteritems():
			self.emit(QtCore.SIGNAL('updated(int,PyQt_PyObject)'), idxes[smp], multiget)
			
		self.idx=idx
		# Emit set_idx() signal only if it is playing
		if self.isRunning():
			self.emit(QtCore.SIGNAL('set_idx(int)'),self.idx)
		
	def run(self):
		if not self.doc:
			logging.debug('%s', 'No document defined!')
			self.stream=False
			return
		self.set_idx(self.idx)
		while self.stream:
			self.set_idx(self.idx+1)
			sleep(self.sleep)
		self.stream=0
		self.idx=0
	
	def toggle_run(self,do=None):
		if do==True:
			if self.isRunning(): return
			self.stream = 1
			self.start()
			return
		elif do==False:
			if not self.isRunning(): return
			self.stream = 0
			self.idx=0
			self.terminate()
			return
		else:
			self.toggle_run(not self.isRunning())
	