#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Live data retrieve and processing"""

from misura.canon.logger import Log as logging
from time import sleep, time
from cPickle import loads
from misura.client import _
from PyQt4 import QtGui, QtCore


class FrameProcessor(QtCore.QThread):
	"""Separate thread to get frames from webcams"""
	#TODO: move into beholder
	data=None
	pp=False
	stream=False
	analysis=False
	compression='png'
	def __init__(self, cam, parent=None):
		self.params = {}
		QtCore.QThread.__init__(self, parent)
		self.cam = cam
		self.waiting = 0.1
		
#	@profile
	def run(self):
		self.cam = self.cam.copy()
		self.cam.connect()
		self.setPriority(QtCore.QThread.IdlePriority)
		self.time = time()
		self.compression=self.cam['compression']
		self.count = 0.
#		frame_number = self.cam.get('frame_number')
		frame_number=0
		force = True
		#Create new cam object with connection unique to this thread.
#		logging.debug('%s %s', 'FRAMEPROCESSOR', type(self.cam))
		tcam = self.cam
		while self.stream:
			if not self.parent().isVisible(): 
				sleep(self.waiting)
				continue
			fr=tcam.frame(frame_number, force)
			if not fr:
				self.stream=False
				continue
			crop, frs, frame_number = fr
			if force: force = False
			if frs is False:
				sleep(self.waiting)
				continue
			# Emit cropping region signal
			self.emit(QtCore.SIGNAL('crop(int,int,int,int)'),*crop)
			t0=time()
			n=-1
			r=0
			for ent in frs:
				n+=1
				if not ent:
					continue
#				logging.debug('%s', ent)
				x,y,w,h,fr=ent
				# Create a QImage for signalling
				img=QtGui.QImage()
				img.loadFromData(QtCore.QByteArray(fr.data),self.compression)
#				print 'FrameProcessor.readyImage',n,x,y,w,h,len(fr.data)
				self.emit(QtCore.SIGNAL('readyImage(int,int,int,int,int,QImage)'),n,x,y,w,h,img)
				r+=1
			# Update counter only for good frames
			if r>0:
				self.count += 1.
				if self.count % 10 == 0:
					fps = self.count / (time() - self.time)
					self.emit(QtCore.SIGNAL('fps(float)'), fps)
					self.time = time()
					self.count = 0.
			sleep(0.001)
#			r=raw_input('Press enter for next frame')
		self.exit(0)
		
		
	def toggle_run(self,do=None):
#		logging.debug('%s %s', 'FrameProcessor.toggle_run', do)
		if do==True:
			if not self.isRunning(): 
				self.stream=True
				self.start()
		elif do==False:
			if self.isRunning(): 
				self.stream=False
				self.quit()
		else:
			self.toggle_run(not self.isRunning())			


		
class SampleProcessor(QtCore.QThread):
	"""Separate thread to get analysis results from sample objects"""
	#TODO: merge with FrameProcessor
	stream=False
	def __init__(self, samples=[], parent=None):
		QtCore.QThread.__init__(self, parent)
		self.parent = parent
		self.waiting = 0.5
		self.set_samples(samples)
		self.opt=set()
		self.res=[]
					
	def set_samples(self, samples):
		"""Build a list of ROI"""
		self.terminate()
		self.samples = samples
		self.res = []
		for i,smp in enumerate(self.samples):
			r = smp.multiget(list(self.opt))
			self.res.append(r)
		
#	@profile
	def run(self):
		if len(self.samples) == 0: return
		self.setPriority(QtCore.QThread.IdlePriority)
		first = True
		samples = []
		self.stream=True
		# Create an in-thread copy
		for smp in self.samples:
			smp1 = smp.copy()
			smp1.connect()
			samples.append(smp1)
		while getattr(self, 'parent', False) and self.stream:
			try:
				if not self.parent.isVisible(): 
					sleep(self.waiting); continue
			except:
				break
			for i, smp in enumerate(samples):
				if first: smp.connect()
				r = smp.multiget(list(self.opt-set(['roi', 'crop'])))
#				if not r:
#					logging.debug('%s %s %s', 'Live update failed: multiget returned', r, self.opt)
				if r.has_key('profile'):
					r['profile']=loads(r['profile'].data)
#				print 'SamplePreprocessor.emit',i,r.keys()
				self.emit(QtCore.SIGNAL('updated(int,PyQt_PyObject)'),i, r)
			first = False		
			sleep(self.waiting)
		
	def toggle_run(self,do=None):
#		logging.debug('%s %s', 'SampleProcessor.toggle_run', do)
		if do==True:
			if not self.isRunning(): 
				self.stream=True
				self.start()
		elif do==False:
			if self.isRunning(): 
				self.stream=False
				self.quit()
		else:
			self.toggle_run(not self.isRunning())
