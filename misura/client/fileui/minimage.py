#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import functools
from PyQt4 import QtGui, QtCore
from ...canon import csutil

class MiniImage(QtGui.QWidget):
	"""Image from test chronology"""
	saveDir=False
	decoder=False
	idx=0
	"""Current data index"""
	t=0
	"""Current data time"""
	meta={'T':None}
	"""Current metadata for label"""
	metaChanged=QtCore.pyqtSignal(object)
	"""Emitted when meta label changes keys. Emits new list of keys."""
	
	def __init__(self,doc, datapath=False,curWidth=100,maxWidth=600,minWidth=100,slider=False,parent=None):
		QtGui.QWidget.__init__(self,parent=parent)
		self.lay=QtGui.QVBoxLayout()
		self.lay.setContentsMargins(0,0,0,0)
		self.lay.setSpacing(0)
		self.setLayout(self.lay)
		self.setAcceptDrops(True)
		# Proper image label
		self.lbl_img=QtGui.QLabel(parent=self)
		self.lbl_img.setAcceptDrops(True)
# 		self.lbl_img.dropEvent=self.dropEvent
		self.lbl_img.setPixmap(QtGui.QPixmap())
		self.lay.addWidget(self.lbl_img)
		# Optional Metadata label
		self.lbl_info=QtGui.QLabel(parent=self)
		self.lay.addWidget(self.lbl_info)
		self.lbl_info.hide()
		self.meta={'T':None}
		self.doc=doc
		logging.debug('%s %s', 'datapath', datapath)
		self.decoder=doc.decoders.get(datapath,False)
		self.img=QtGui.QImage()
		self.curWidth=curWidth
		self.defaultWidth=curWidth
		self.maxWidth=maxWidth
		self.minWidth=minWidth
		self.menu=QtGui.QMenu(self)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
		self.menu.addAction('Next', self.next)
		self.menu.addAction('Previous', self.prev)
		self.menu.addAction('Save', self.save_frame)
		self.meta_menu=self.menu.addMenu('Labels')
		# Slider for image navigation
		self.slider=QtGui.QScrollBar(parent=self)
		if self.decoder:
			self.slider.setMaximum(len(self.decoder))
		self.slider.setMinimum(0)
		self.slider.setTracking(False)
		self.slider.setOrientation(QtCore.Qt.Horizontal)
		self.slider.valueChanged.connect(self.set_idx)
		if not slider: self.slider.hide()
		self.connect(self.decoder,QtCore.SIGNAL('cached(int)'),self.cached)
		
	def save_frame(self):
		"""Save current frame"""
		if not self.saveDir:
			self.saveDir = QtGui.QFileDialog.getExistingDirectory(self, "Images destination folder", "/tmp")
		self.img.save('%s/%i.jpg' % (self.saveDir, self.idx), 'JPG',25)
		
	def empty(self):
		"""Set the image as empty"""
		self.lbl_img.setPixmap(QtGui.QPixmap())
		self.lbl_info.hide()
		
	def next(self):
		self.set_idx(self.idx+1)
		
	def prev(self):
		self.set_idx(self.idx-1)
		
	def cached(self,idx):
		if idx==self.idx:
			self.set_idx()

	def set_idx(self,idx=-1):		
		if not self.decoder:
			logging.debug('%s', 'set_idx no decoder')
			return False				
		if idx<0:idx=self.idx
		logging.debug('%s %s', 'set_idx', idx)
		self.idx=idx
		ln=len(self.decoder)
		self.slider.setMaximum(ln)
		if self.idx>=ln:
			logging.debug('%s %s %s', 'Index out of bounds', self.idx, ln)
			return False
		logging.debug('%s %s %s %s', 'getting idx from decoder', self.decoder.datapath, self.decoder.ext, idx)
		img=self.decoder.get(idx)
		
		self.slider.valueChanged.disconnect(self.set_idx)
		logging.debug('%s %s', 'GOT IMG', repr(img))
		if not img: 
			self.img=QtGui.QImage()
		else:
			self.t, self.img=img
			self.emit(QtCore.SIGNAL('set_time(float)'),self.t)
		self.zoom(self.curWidth)
		
		self.slider.setValue(self.idx)
		logging.debug('%s %s', 'sliderValue', self.slider.value())
		self.emit(QtCore.SIGNAL('changedIdx()'))
		self.emit(QtCore.SIGNAL('changedIdx(int)'),self.idx)
		self.slider.valueChanged.connect(self.set_idx)
#		self.setToolTip(metaToText(self.meta,self.decoder.visibleOptions))
		self.update_info()
		return True
	
	def set_time(self,t):
		#TODO: implement this in order to be introduce time stepping in slider.
		# This will in turn enable value stepping.
		self.update_info()
	
	def update_info(self):
		"""Update info label"""
		if not self.doc.data.has_key('0:t'):
			logging.debug('%s', 'No time dataset still')
			self.lbl_info.hide()
			return False
		# Base dataset path name
		p=self.decoder.datapath.split('/') 
		# Remove last name (/profile or /frame)
		p.pop(-1)
		p='/'.join(p)
		logging.debug('%s %s', 'update_info', p)
		
		# Document-based index
		idx=csutil.find_nearest_val(self.doc.data['0:t'].data,self.t)
		for k in self.meta.keys():
			if k=='T':
				p1='0:kiln/'+k
			else:
				p1='0:'+p[1:]+'/'+k
			ds=self.doc.data.get(p1,None)
			if ds is None:
				logging.debug('%s %s %s', 'update_info: no target dataset was found', k, p1)
				continue
			self.meta[k]=ds.data[idx]
			
		msg=''
		for k,v in self.meta.items():
			if v is None:
				continue
			msg+='{}: {:.2f}\n'.format(k,v)
		if not len(msg):
			logging.debug('%s %s', 'No metadata to update', self.meta)
			self.lbl_info.hide()
			return False
		self.lbl_info.setText(msg[:-1])
		self.lbl_info.show()
		return True
	
	def dragEnterEvent(self,event):
		logging.debug('%s %s', 'dragEnterEvent', event.mimeData())
		event.acceptProposedAction()
		if event.mimeData().hasFormat("text/plain"):
			event.acceptProposedAction()
	
	def dropEvent(self,event):
		logging.debug('%s', 'DROP EVENT')
		opt=str(event.mimeData().text()).replace('summary', '').replace('//', '/').split('/')[-1]
		logging.debug('%s %s', 'Adding sample option:', opt)
		self.meta[opt]=0
		self.update_info()
		self.metaChanged.emit(self.meta.keys())
		
	def sync_meta_keys(self,keys):
		"""To be connected with metaChanged signal from other mini images"""
		new=set(keys)
		old=set(self.meta.keys())
		logging.debug('%s %s %s', 'sync', new, old)
		for k in new-old:
			self.meta[k]=0
		for k in old-new:
			del self.meta[k]
		if new!=old:
			self.update_info()
				
		
	def minimumSizeHint(self):
		return self.lbl_img.pixmap().size()
	
	def sizeHint(self):
		return self.lbl_img.pixmap().size()
		
	def showMenu(self, pt):
		self.meta_menu.clear()
		self.meta_act=[]
		for k in self.meta.keys():
			f=functools.partial(self.del_meta,k)
			a=self.meta_menu.addAction(k,f)
			self.meta_act.append((a,f))
		
		self.menu.popup(self.mapToGlobal(pt))
		
	def del_meta(self,k):
		if not self.meta.has_key(k):
			return False
		del self.meta[k]
		self.metaChanged.emit(self.meta.keys())
		self.update_info()
		
	def zoom(self, width=0):
		logging.debug('%s', 'zooming')
		if not width: width=self.defaultWidth
		width=min(width,self.maxWidth)
		width=max(width,self.minWidth)
		self.curWidth=width
		pix=QtGui.QPixmap.fromImage(self.img)
		pix=pix.scaledToWidth(width)
		self.lbl_img.setPixmap(pix)
	def zoomIn(self):
		self.zoom(self.curWidth*1.1)
	def zoomOut(self):
		self.zoom(self.curWidth*0.9)
		
	def wheelEvent(self,event):
		d=event.delta()
		if d==0: return
		if d>0:
			self.zoomOut()
		else: 
			self.zoomIn()
		
	def copy(self):
		new=MiniImage(self.doc,self.decoder.datapath,parent=self,curWidth=self.img.width(),maxWidth=self.img.width()*4,slider=True)
		new.set_idx(self.idx)
# 		new.zoom()
		return new
	
	def mouseDoubleClickEvent(self,event):
		"""Opens a dialog containing a new MiniImage instance"""
		logging.debug('%s', event)
		self.new=self.copy()
		dia=ImageDialog(self.new,parent=self)
		dia.show()
		
class ImageDialog(QtGui.QDialog):
	"""Show a MiniImage in a separate dialog"""
	def __init__(self,mini,parent=None):
		QtGui.QDialog.__init__(self,parent=parent)
		self.lay=QtGui.QHBoxLayout()
		self.setLayout(self.lay)
		self.mini=mini
		self.lay.addWidget(self.mini)
		# Problem: fixed sync!
# 		self.meta=RowView(parent=self)
# 		self.meta.set_doc(mini.doc)
# 		self.meta.model().refresh()
# # 		self.meta.set_idx(self.mini.idx)
# 		self.lay.addWidget(self.meta)

