#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from .. import _
from .. import filedata
from .. import fileui
from .. import acquisition
from ..live import registry
from misura.canon.csutil import profile

class TestWindow(acquisition.MainWindow):
	"""View of a single test file"""
	def __init__(self,doc,parent=None):
		acquisition.MainWindow.__init__(self,doc=doc,parent=parent)
		self.play=filedata.FilePlayer(self)
		self.play.set_doc(doc)
		self.play.sleep=0.1
		self.load_version(-1)
		
		self.controls.server=self.play
# 		self.controls.remote=self.play
		for pic,win in self.cameras.itervalues():
			pic.setSampleProcessor(self.play)
# 			d=self.doc.decoders['/dat/'+pic.role]
# 			pic.setFrameProcessor(d)
			
		self.graphWin.show()
#		self.summaryPlot.default_plot()
		self.removeToolBar(self.controls)
		self.connect(self.play, QtCore.SIGNAL('set_idx(int)'),self.set_idx)
		self.connect(self.snapshotsTable,QtCore.SIGNAL('set_idx(int)'),self.play.set_idx)
		
	@property
	def tasks(self):
		return registry.tasks
		
# 	@profile
	def load_version(self,v=-1):
		print "SETTING VERSION",v
		if not self.fixedDoc.proxy.isopen():
			self.fixedDoc.proxy.reopen()
		self.fixedDoc.proxy.set_version(v)
		if self.fixedDoc.proxy.conf is False:
			self.fixedDoc.proxy.load_conf()
		self.setServer(self.fixedDoc.proxy.conf)
		self.name=self.fixedDoc.proxy.get_node_attr('/conf','instrument')
		print 'instrument name',self.name,	getattr(self.fixedDoc.proxy.conf,self.name)
		self.snapshotsTable.slider.choice()
		self.snapshotsTable.strip.set_idx()
		self.title=self.remote.measure['name']
		self.setWindowTitle('Test: '+self.remote.measure['name'])
		
		# Menu Bar mod
		self.myMenuBar.connectTo.hide()
		self.myMenuBar.help.hide()
		self.actStandard=self.myMenuBar.measure.addAction(_('Re-evaluate standards'),self.re_standard)
		
		self.menuVersions=fileui.VersionMenu(self.fixedDoc.proxy)
		self.myMenuBar.measure.addMenu(self.menuVersions)
		self.menuVersions.versionChanged.connect(self.load_version)
		
	def close(self):
		self.play.close()
		self.fixedDoc.proxy.close()
		acquisition.MainWindow.close(self)
		
	def set_idx(self,idx):
		print 'TestWindow.set_idx',self.play.isRunning(),idx
		if not self.play.isRunning():
			self.play.set_idx(idx)
		else:
			if idx==self.snapshotsTable.slider.slider.value(): 
				return
			self.snapshotsTable.set_idx(idx)
			
	def re_standard(self):
		"""Re-evaluate the meta-data generating scripts (standards)."""
		fp=self.fixedDoc.proxy
		if fp.__class__.__name__!='SharedFile':
			print 'Error: restandard is only possible on local files'
			return
		# Overwrite
		r=self.fixedDoc.proxy.run_scripts(self.remote)
		if r:
#			# Update every ActiveWidget connected to the registry
			registry.force_redraw()
			self.summaryPlot.resize(self.summaryPlot.size())
			

			
		
