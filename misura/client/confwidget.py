#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui,QtCore
from misura.client.widgets.active import Linguist
from misura.client.clientconf import confdb, settings
import functools
import os

class Path(Linguist,QtGui.QWidget):
	def __init__(self,path,parent=None):
		QtGui.QWidget.__init__(self,parent)
		Linguist.__init__(self,context='Client')
		self.lay=QtGui.QHBoxLayout()
		self.setLayout(self.lay)
		self.lay.addWidget(QtGui.QLabel(self.mtr('Configuration File:')))
		self.line=QtGui.QLineEdit(self)
		self.line.setText(path)
		self.lay.addWidget(self.line)
		self.button=QtGui.QPushButton(self)	
		self.button.setText(self.mtr('Open'))
		self.lay.addWidget(self.button)
		self.connect(self.button,QtCore.SIGNAL('clicked()'),self.change)
		
		self.btn_reload=QtGui.QPushButton(self)	
		self.btn_reload.setText(self.mtr('Reload'))
		self.lay.addWidget(self.btn_reload)
		self.connect(self.btn_reload,QtCore.SIGNAL('clicked()'),self.reload)
		
		self.btn_save=QtGui.QPushButton(self)	
		self.btn_save.setText(self.mtr('Save'))
		self.lay.addWidget(self.btn_save)
		self.connect(self.btn_save,QtCore.SIGNAL('clicked()'),self.save)
		
	def reload(self):
		self.emit(QtCore.SIGNAL('newDb()'))
		
	def save(self):
		confdb.save()
		
	def change(self):
		path=QtGui.QFileDialog.getOpenFileName(parent=self, caption=self.mtr("Client configuration path"))
		if not path: return
		self.line.setText(path)
		self.reload()
		
class ClientConf(Linguist,QtGui.QWidget):
	def __init__(self,parent=None):
		QtGui.QWidget.__init__(self,parent)
		Linguist.__init__(self,context='Client')
		self.lay=QtGui.QVBoxLayout()
		self.setLayout(self.lay)
		self.path=Path(confdb.path,self)
		self.lay.addWidget(self.path)
		from misura.client import conf
		self.conf=conf.Interface(confdb, confdb, confdb.describe())
		self.lay.addWidget(self.conf)
		self.connect(self.path,QtCore.SIGNAL('newDb()'),self.change)
		self.connect(self.path,QtCore.SIGNAL('save()'),confdb.save)
		
	def change(self):
		path=str(self.path.line.text())
		r=confdb.load(path)
		self.conf.close()
		del self.conf
		from misura.client import conf
		self.conf=conf.Interface(confdb, confdb, confdb.describe())
		self.lay.addWidget(self.conf)
		settings.setValue('/Configuration',path)
		
class RecentInterface(Linguist):
	"""Common functions"""
	def __init__(self,conf,category):
		Linguist.__init__(self,context='Client')
		self.category=category
		self.conf=conf
		self.name=category
		if self.name=='m3database': 
			self.name='Misura3 database'
			self.label=self.name
		else:
			self.label='Recent {}'.format(self.name.capitalize())
		self.sig_select=QtCore.SIGNAL('select(QString)')
	
	def getNameSigList(self):
		tab=getattr(self.conf,'recent_'+self.category)
		print 'getNameSigList',self.category,tab
		nsl=[]
		for i,row in enumerate(tab):
			sig=row[0]
			name=row[0]
			if self.category=='file':
				if row[1]!='': name=row[1]+' ('+row[0]+')'
			if self.category=='server':
				name0=row[0].replace('//','/').split('/')[1]
				name=row[1]+'@'+name
#				sig='https://%s:%s@%s/RPC' % (row[1],row[2],name0)
			nsl.append([name,sig])
		return nsl
	
	def clear_recent(self):
		setattr(self.conf,'recent_'+self.category,[])
		self.conf.save()
		self.conf.emit(QtCore.SIGNAL('rem()'))
		
	def new(self,*a):
		if self.category in ['server']:
			path=QtGui.QInputDialog.getText(self, self.mtr('Specify a new server address'), self.mtr('Address'),text='https://IP/RPC')[0]
		else:
			tab=getattr(self.conf,'recent_'+self.category)
			print 'new: tab',self.category,tab
			d=''
			if len(tab)>0:
				d=os.path.dirname(tab[-1][0])
			path=QtGui.QFileDialog.getOpenFileName(self, self.mtr("Open a new ")+self.category, d)
		if not path: return
		self.emit(QtCore.SIGNAL('new(QString)'),path)
		self.emit(QtCore.SIGNAL('select(QString)'),path)	


class RecentMenu(RecentInterface, QtGui.QMenu):
	"""Recent objects menu"""
	def __init__(self,conf,category,parent=None):
		QtGui.QMenu.__init__(self,parent=parent)
		RecentInterface.__init__(self,conf,category)
		self.setTitle(self.mtr('Recent '+self.name+'s'))
		self.redraw()
		self.connect(self.conf,QtCore.SIGNAL('mem()'),self.redraw)
		self.connect(self.conf,QtCore.SIGNAL('rem()'),self.redraw)
		self.connect(self,QtCore.SIGNAL('aboutToShow()'),self.redraw)
		
	def redraw(self):
		self.clear()
		nsl=self.getNameSigList()
		for name,sig in nsl:
			p=functools.partial(self.emit, QtCore.SIGNAL('select(QString)'), sig)
			self.addAction(name,p)
		self.addSeparator()
		self.addAction(self.mtr("Clear list"),self.clear_recent)
		self.addAction(self.mtr("Open")+'...',self.new)
		if self.category=='server':
			self.addAction(self.mtr('Disconnect'),self.server_disconnect)
			self.addAction(self.mtr('Restart'),self.server_restart)
			self.addAction(self.mtr('Shutdown'),self.server_shutdown)
			
	def server_disconnect(self):
		self.emit(QtCore.SIGNAL('server_disconnect()'))
	def server_shutdown(self):
		self.emit(QtCore.SIGNAL('server_shutdown()'))
	def server_restart(self):
		self.emit(QtCore.SIGNAL('server_restart()'))
		
class RecentWidget(RecentInterface, QtGui.QWidget):
	"""Recent objects list widget"""
	def __init__(self,conf,category,parent=None):
		QtGui.QWidget.__init__(self,parent)
		RecentInterface.__init__(self,conf,category)
		self.setWindowTitle(self.mtr('Recent '+self.name+'s:'))
		self.lay=QtGui.QVBoxLayout()
		
		self.lay.addWidget(QtGui.QLabel('Recent '+self.name+'s:'))
		
		self.list=QtGui.QListWidget(self)
		self.connect(self.list, QtCore.SIGNAL('itemDoubleClicked(QListWidgetItem *)'), self.select_item)
		self.connect(self.conf,QtCore.SIGNAL('mem()'),self.redraw)
		self.connect(self.conf,QtCore.SIGNAL('rem()'),self.redraw)
		self.lay.addWidget(self.list)
		
		self.button=QtGui.QPushButton(self.mtr('Open')+'...',parent=self)
		self.connect(self.button,QtCore.SIGNAL('clicked()'),self.new)
		self.lay.addWidget(self.button)
		
		self.redraw()
		self.setLayout(self.lay)
		
	def redraw(self):
		"""Updates the list"""
		self.list.clear()
		nsl=self.getNameSigList()
		for name,sig in nsl:
			item=QtGui.QListWidgetItem(name)
			# Assign to the item userdata the path of the object, which will be emitted in select_item
			item.setData(QtCore.Qt.UserRole,sig)
			self.list.addItem(item)
		
			
	def select_item(self,item):
		"""Emit the 'select(QString)' signal with the path of the object"""
		self.emit(self.sig_select,item.data(QtCore.Qt.UserRole))
		

class Greeter(QtGui.QWidget):
	"""Group of recent object widgets, for file, database and server items."""
	def __init__(self,parent=None):
		QtGui.QWidget.__init__(self,parent)
		self.lay=QtGui.QHBoxLayout()
		self.setWindowTitle('Recent data sources')
		
		self.file=RecentWidget(confdb,'file',self)
		self.lay.addWidget(self.file)
		self.database=RecentWidget(confdb,'database',self)
		self.lay.addWidget(self.database)
		self.server=RecentWidget(confdb,'server',self)
		self.lay.addWidget(self.server)
		
		self.setLayout(self.lay)
		
