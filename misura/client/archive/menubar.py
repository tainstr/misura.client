#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore

from misura.client import conf
from misura.client import widgets
from misura.client.clientconf import confdb
from misura.client.confwidget import RecentMenu

class ArchiveMenuBar(widgets.Linguist,QtGui.QMenuBar):
	"""Menu principali"""
	def __init__(self, server=False, parent=None):
		QtGui.QMenuBar.__init__(self, parent)
		widgets.Linguist.__init__(self,context='Acquisition')
		
		self.lstActions=[]
		self.func=[]
		self.file=self.addMenu(self.mtr('File'))
		
		self.recentFile=RecentMenu(confdb,'file',self)
		self.actFile=self.file.addAction(self.mtr('Open File'), self.recentFile.new)
		act=self.addMenu(self.recentFile)
		
		self.recentDatabase=RecentMenu(confdb,'database',self)
		self.actDb=self.file.addAction(self.mtr('Open Database'), self.recentDatabase.new)
		self.addMenu(self.recentDatabase)
		
		self.actNewDb=self.file.addAction(self.mtr('New Database'), self.new_database)
		
		self.recentServer=RecentMenu(confdb,'server',self)
#		self.connect(self.recentServer,QtCore.SIGNAL('new(QString)'),self.open_server)
		self.addMenu(self.recentServer)
		
		self.recentM3db=RecentMenu(confdb,'m3database',self)
#		self.connect(self.recentM3db,QtCore.SIGNAL('new(QString)'),self.open_database)
		self.file.addMenu(self.recentM3db)
		
		self.currents=self.addMenu(self.mtr('View Tests'))
		self.databases=self.addMenu(self.mtr('View Databases'))
		
		
		
	def new_database(self,path=False):
		if not path:
			path=QtGui.QFileDialog.getSaveFileName(self,"Choose a name for the new database","C:\\")
		if not path: return
		self.emit(QtCore.SIGNAL('new_database(QString)'),path)
		
	def eval_standard(self):
		self.emit(QtCore.SIGNAL('re_standard()'))