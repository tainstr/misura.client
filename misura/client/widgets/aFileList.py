#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from misura.client.widgets.active import *
from aChooser import aChooser
from .. import _
from ..sync import TransferThread


class aFileList(aChooser):
	
	def __init__(self, *a,**kw):

		aChooser.__init__(self, *a,**kw)
		#TODO: make menu and add Download, Delete, Rename,... like in presets.
		self.bSend=QtGui.QPushButton('Send')
		self.bSend.setMaximumWidth(40)
		self.connect(self.bSend, QtCore.SIGNAL('clicked(bool)'), self.send)
		self.lay.addWidget(self.bSend)
		self.prevIdx=0
		self.transfer=False

	def send(self, *args):
		n=QtGui.QFileDialog.getOpenFileName(parent=self,caption=_("Upload File"))
		if len(n)==0 or not os.path.exists(n):
			print 'File Upload Aborted'
			return
		url=self.remObj.conn_addr+self.remObj['fullpath'][:-1] # remove trailing /
		print 'Transfer target:',repr(url),n,self.handle
		self.transfer=TransferThread(url=url,outfile=n,post={'opt':self.handle})
		from ..live import registry
		self.transfer.set_tasks(registry.tasks)
		self.transfer.start()
		self.redraw()
		
