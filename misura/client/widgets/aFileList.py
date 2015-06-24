#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from misura.client.widgets.active import *
from aChooser import aChooser
from .. import _
from ..network import TransferThread
from misura.canon.logger import Log as logging


class aFileList(aChooser):
	
	def __init__(self, *a,**kw):
		"""Widget representing a FileList option type, allowing to upload a new file via the stream interface."""
		aChooser.__init__(self, *a,**kw)
		#TODO: make menu and add Download, Delete, Rename,... like in presets.
		self.bSend=QtGui.QPushButton('Send')
		self.bSend.setMaximumWidth(40)
		self.connect(self.bSend, QtCore.SIGNAL('clicked(bool)'), self.send)
		self.lay.addWidget(self.bSend)
		self.prevIdx=0
		self.transfer=False

	def send(self, *args):
		"""Upload local file"""
		n=QtGui.QFileDialog.getOpenFileName(parent=self,caption=_("Upload File"))
		if len(n)==0 or not os.path.exists(n):
			logging.debug('%s', 'File Upload Aborted')
			return
		if os.path.basename(n) in self.prop['options']:
			#TODO: allow to overwrite....
			QtGui.QMessageBox.warning(self,_('Overwriting file'),_('A file with the same name already exists.\nPlease choose a different one.'))
			return 
		url=self.remObj.conn_addr+self.remObj['fullpath'][:-1] # remove trailing /
		logging.debug('%s %s %s %s', 'Transfer target:', repr(url), n, self.handle)
		self.transfer=TransferThread(url=url,outfile=n,post={'opt':self.handle})
		from ..live import registry
		self.transfer.set_tasks(registry.tasks)
		self.transfer.start()
		self.redraw()
		
