#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import widgets, network, conf
from ..clientconf import confdb
from ..connection import LoginWindow, addrConnection
from ..confwidget import RecentMenu
from .. import parameters as params

from PyQt4 import QtGui, QtCore
import functools

class MenuBar(widgets.Linguist,QtGui.QMenuBar):
	"""Menu principali"""
	def __init__(self, server=False, parent=None):
		QtGui.QMenuBar.__init__(self, parent)
		widgets.Linguist.__init__(self,context='Acquisition')
		self.remote=False
		self.server=server
		self.windows={}
		self.objects={}
		self.lstActions=[]
		self.func=[]
		if self.fixedDoc is False:
			self.set_acquisition_mode()
		else:
			self.set_archive_mode()
		self.measure=self.addMenu(self.mtr('Measure'))
		self.connect(self.measure, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
		self.settings=self.addMenu(self.mtr('Settings'))
		self.connect(self.settings, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
		if self.fixedDoc is False:
			self.measure.setEnabled(False)
			self.settings.setEnabled(False)
		self.help=self.addMenu('Help')
		if server is not False: 
			self.setServer(server)

	@property
	def fixedDoc(self):
		if self.parent() is None:
			return False
		return self.parent().fixedDoc		
	
	def set_acquisition_mode(self):
		self.connectTo=self.addMenu(self.mtr('Connect'))
		self.servers=RecentMenu(confdb,'server',self)
		self.servers.setTitle('Server')
		self.connect(self.servers,QtCore.SIGNAL('select(QString)'),self.setAddr)
		self.connectTo.addMenu(self.servers)
		self.instruments=self.connectTo.addMenu('Instruments')
		self.instruments.setEnabled(False)
		self.actLogout=self.connectTo.addAction(self.mtr('Logout'), self.logout)
		self.actLogout.setEnabled(False)
		self.actShutdown=self.connectTo.addAction(self.mtr('Shutdown'), self.shutdown)
		self.actShutdown.setEnabled(False)
	
	def set_archive_mode(self):
		self.connectTo=QtGui.QMenu()
		self.instruments=QtGui.QMenu()
		#		self.chooser.setView(self.tree)
	
	def setAddr(self,addr):
		addr=str(addr)
		obj=addrConnection(addr)
		if not obj: 
			print 'MenuBar.setAddr: Failed!'
			return
		network.setRemote(obj)
		
	def logout(self):
		if not self.server: return
		r=self.server.users.logout()
		confdb.logout(self.server.addr)
		QtGui.QMessageBox.information(self, 'Logged out',
			'You have been logged out (%s): \n %r' % (network.manager.user, r))
		
	def shutdown(self):
		QtGui.QMessageBox.information(self, 'Shutting Down',
			'Server is shutting down:\n %r' % network.manager.remote.shutdown())		

	def getConnection(self, srv):
		LoginWindow(srv.addr, srv.user, srv.password, parent=self).exec_()

	def setServer(self,server=False):
		self.instruments.clear()
		### INSTRUMENTS Submenu
		self.lstInstruments=[]
		self.server=server
		if not server:
			self.server=network.manager.remote
		
		if self.fixedDoc: inslist=[]
		else: inslist=self.server['instruments']
		for (title, name) in  inslist:
			opt='eq_'+name
			if self.server.has_key(opt):
				if not self.server[opt]:
					print 'Disabled instrument',opt, self.server[opt]
					continue					
			elif not params.debug:
				print 'Skipping unknown instrument',name
				continue
			obj=getattr(self.server, name,False)
			if not obj:
				print 'missing handler',name
				continue
			f=functools.partial(self.parent().setInstrument, obj)
			act=self.instruments.addAction('%s (%s)' % (title, obj['comment']), f)
			self.func.append(f)
			self.lstInstruments.append((act, title))
		self.appendGlobalConf()
		#Enable menu and menu items after server connection
		if self.fixedDoc is False:
			self.instruments.setEnabled(True)
			self.actLogout.setEnabled(True)
			self.actShutdown.setEnabled(True)
			self.settings.setEnabled(True)
		print 'lstInstruments', self.lstInstruments
		
	def get_window(self,key):
		d=self.windows.get(key,False)
		if not d and self.objects.has_key(key):
			d=self.objects[key]()
			self.windows[key]=d
		elif not d: 
			d=key
		return d		
	
	def hideShow(self, key):
		d=self.get_window(key)
		if d.isVisible():
			d.hide()
		else:
			d.show()

	def setInstrument(self, remote,server=False):
		self.setServer(server)
		self.remote=remote
		self.lstActions=[]
		parent=self.parent()
		name=self.remote['name']
		for act, aname in self.lstInstruments:
			if aname==name:
				act.setCheckable(True)
				act.setChecked(True)
				break
		### MEASURE Menu
		self.measure.clear()
		if not self.fixedDoc:
			self.measure.addAction('Initialize New Test', self.parent().init_instrument)
			self.measure.addAction('Delayed start', self.parent().delayed_start)
		#TODO: Share windows definitions with mainwin?
		self.windows['measureDock']=parent.measureDock
		self.showMeasureDock=functools.partial(self.hideShow, 'measureDock')
		act=self.measure.addAction('Test Configuration', self.showMeasureDock)
		self.lstActions.append((act, 'measureDock'))
			
		self.windows['snapshotsDock']=parent.snapshotsDock
		self.showSnapshotsStrip=functools.partial(self.hideShow, 'snapshotsDock')
		act=self.measure.addAction('Snapshots', self.showSnapshotsStrip)
		self.lstActions.append((act, 'snapshotsDock'))
		
		self.windows['graphWin']=parent.graphWin
		self.showGraph=functools.partial(self.hideShow, 'graphWin')
		act=self.measure.addAction('Data Plot', self.showGraph)
		self.lstActions.append((act, 'graphWin'))
		
		self.windows['tableWin']=parent.tableWin
		self.showTable=functools.partial(self.hideShow, 'tableWin')
		act=self.measure.addAction('Data Table', self.showTable)
		self.lstActions.append((act, 'tableWin'))

		self.windows['logDock']=parent.logDock
		self.showLogWindow=functools.partial(self.hideShow, 'logDock')
		act=self.measure.addAction('Log Window', self.showLogWindow)
		self.lstActions.append((act, 'logDock'))
		
		self.measure.addAction('Reload data',self.reload_data)
		
		if self.fixedDoc:
			self.measure.addSeparator()
			self.measure.addAction('Save to file')
			self.measure.addAction('Close')
		else:
			self.measure.addAction('Quit Client')
		self.measure.setEnabled(True)

		### SETTINGS Menu
		self.settings.clear()
		self.showInstrumentConf=functools.partial(self.hideShow, 'iconf')
		act=self.settings.addAction('Instrument', self.showInstrumentConf)
		self.objects['iconf']=functools.partial(conf.Interface, self.server,  self.remote)
		self.lstActions.append((act, self.remote))
		
		###### DEVICES SubMenu
		self.devices=self.settings.addMenu('Devices')
		self.connect(self.devices, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
		paths=self.remote['devices']

		for path in paths:
			role,path=path
			lst=self.server.searchPath(path)
			if lst is False:
				print 'Undefined path for role', role,path
				continue
			obj=self.server.toPath(lst)
			if obj is None: 
				print 'Path not found'
				continue
			self.addDevConf(obj, role)
		self.appendGlobalConf()
		
		for act, cf in self.lstActions:
			act.setCheckable(True)

	def appendGlobalConf(self):
		self.objects['mconf']=functools.partial(conf.MConf,self.server)
		self.showMConf=functools.partial(self.hideShow, 'mconf')
		act=self.settings.addAction('Global', self.showMConf)
		act.setCheckable(True)
		self.lstActions.append((act, 'mconf'))
	
	def addDevConf(self, obj, role):
		self.objects[obj]=functools.partial(conf.Interface, self.server, obj)
		f=functools.partial(self.hideShow, obj)
		act=self.devices.addAction('%s (%s)' % (role, obj['name']), f)
		self.lstActions.append((act, obj))

	def updateActions(self):
		for act, key in self.lstActions:
			conf=self.windows.get(key, False)
			if not conf: continue
			conf=self.get_window(key)
			if not conf: continue
			if type(conf)==type(''): continue
			if hasattr(conf, '_Method__name'): continue
			print 'Updating',conf
			act.setChecked(conf.isVisible())

	def reload_data(self):
		self.parent().uid=False
		self.parent().resetFileProxy()
