#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
import functools
import tables
from time import sleep
import threading
from traceback import print_exc


from ..live import registry
from .. import network

from .. import widgets, beholder
from .. import fileui, filedata, navigator
from ..misura3 import m3db
from ..connection import ServerSelector, LiveLog
from .menubar import MenuBar
from .selector import InstrumentSelector
from .measureinfo import MeasureInfo
from .controls import Controls
from .delay import DelayedStart 

from .. import graphics
from ..database import UploadThread
from ..filedata import RemoteFileProxy 

from misura.canon import csutil

subWinFlags=QtCore.Qt.CustomizeWindowHint|QtCore.Qt.WindowTitleHint|QtCore.Qt.WindowMinMaxButtonsHint
roles={'motorBase':'Base Position', 'motorHeight':'Height Position',
                'motorRight':'Right Position', 'motorLeft':'Left Position',
                'focus':'Focus adjust', 'motor':'Position', 'camera':'Main',
                'cameraBase':'Base', 'cameraHeight':'Height', 'cameraRight':'Right',
                'cameraLeft':'Left', 'force':'Weight',
                'angleHeight':'Height Inclination','angleBase':'Base Inclination',
                'angleRight':'Right Inclination','angleLeft':'LeftInclination'}

class MainWindow(QtGui.QMainWindow, widgets.Linguist):
	"""Generalized Acquisition Interface"""
	remote=None
	doc=False
	uid=False
	
	@property
	def tasks(self):
		# DEBUG needed for UT
		if not registry.tasks:
			registry.set_manager(network.manager)
			if self.server and not self.fixedDoc:
				registry.progress.set_server(self.server)
		return registry.tasks
	
	def __init__(self, doc=False, parent=None):
		super(MainWindow, self).__init__(parent)
		widgets.Linguist.__init__(self,context='Acquisition')
		self._lock=threading.Lock()
		self.cameras={}
		self.toolbars=[]
		self.fixedDoc=doc
		self.server=False
		self.area=QtGui.QMdiArea()
		self.setCentralWidget(self.area)
		self.setMinimumSize(800,600)
		self.setWindowTitle(self.mtr('Misura Live'))
		self.myMenuBar=MenuBar(parent=self)
		self.setMenuWidget(self.myMenuBar)
		self.connect(network.manager, QtCore.SIGNAL('connected()'), self.setServer)	
		self.add_server_selector()

	def add_server_selector(self):
		"""Server selector dock widget"""
		self.serverDock=QtGui.QDockWidget(self.centralWidget())
		self.serverSelector=ServerSelector(self.serverDock)
		self.serverDock.setWindowTitle(self.serverSelector.label)
		self.serverDock.setWidget(self.serverSelector)
		self.addDockWidget(QtCore.Qt.TopDockWidgetArea,self.serverDock)
		
	def close(self):
		self.timer.stop()
		return QtGui.QMainWindow.close(self)
		
	def rem(self, d, w=False):
		"""Removes a widget by name"""
		d=getattr(self, d, False)
		if not d: return
		self.removeDockWidget(d)
		d.deleteLater()
		if not w: return
		w=getattr(self, w,False)
		if w: w.deleteLater()
		
	def stopped_nosave(self):
		"""Reset the instrument, completely discarding acquired data and remote file proxy"""
		print "STOPPED_NOSAVE"
		#TODO: reset ops should be performed server-side
		self.remote.measure['uid']=''
		self.resetFileProxy()

	def setServer(self, server=False):
		print 'Setting server to',server
		self.server=server
		if not server:
			network.manager.remote.connect()
			self.server=network.manager.remote
		self.serverDock.hide()
		self.myMenuBar.close()
		del self.myMenuBar
		self.myMenuBar=MenuBar(server=self.server,parent=self)
		self.rem('logDock')
		self.logDock=QtGui.QDockWidget(self.centralWidget())
		self.logDock.setWindowTitle('Log Messages')
		if self.fixedDoc:
			self.logDock.setWidget(fileui.OfflineLog(self.fixedDoc.proxy,self.logDock))
		else:
			self.logDock.setWidget(LiveLog(self.logDock))		
		self.addDockWidget(QtCore.Qt.BottomDockWidgetArea,self.logDock)
		
		self.setMenuBar(self.myMenuBar)
		
		
		self.rem('instrumentDock')
		self.instrumentDock=QtGui.QDockWidget(self.centralWidget())
		self.instrumentSelector=InstrumentSelector(self,self.setInstrument)
		self.instrumentDock.setWidget(self.instrumentSelector)
		self.addDockWidget(QtCore.Qt.TopDockWidgetArea,self.instrumentDock)
		print self.server.describe()
		ri=self.server['runningInstrument'] # currently running
		li=ri
		if self.server.has_key('lastInstrument'): # compatibility with old tests
			li=self.server['lastInstrument'] # configured, ready, finished
		if ri in ['None','']:
			ri=li
		if ri not in ['None','']:
			remote=getattr(self.server,ri)
			self.setInstrument(remote)
		if self.fixedDoc:
			return
		# Automatically pop-up delayed start dialog
		if self.server['delayStart']:
			self.delayed_start()
		
			
	def add_measure(self):
		# MEASUREMENT INFO
		self.rem('measureDock', 'measureTab')
		self.measureDock=QtGui.QDockWidget(self.centralWidget())
		self.measureDock.setWindowTitle(' Test Configuration')
		self.measureTab=MeasureInfo(self.remote, self.fixedDoc, parent=self.measureDock)
		self.measureDock.setWidget(self.measureTab)
		self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.measureDock)
		
	def add_snapshots(self):
		# SNAPSHOTS
		self.rem('snapshotsDock', 'snapshotsStrip')
		self.snapshotsDock=QtGui.QDockWidget(self.centralWidget())
		self.snapshotsDock.setWindowTitle('Snapshots')
		self.snapshotsTable=fileui.ImageSlider()
		self.snapshotsDock.setWidget(self.snapshotsTable)
		self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.snapshotsDock)
		if self.name not in ['hsm','post','drop']:
			self.snapshotsDock.hide()
			
	def add_sumtab(self):
		# SUMMARY TREE - In lateral measureTab
		self.navigator=navigator.Navigator(parent=self,mainwindow=self.summaryPlot,cols=2)
		self.summaryPlot.connect(self.summaryPlot,QtCore.SIGNAL('hide_show(QString)'),self.navigator.plot)
		self.measureTab.results=self.navigator
		self.measureTab.refreshSamples()
	
	def add_graph(self):
		# PLOT window
		w=getattr(self, 'summaryPlot', False)
		g=getattr(self, 'graphWin', False)
		if w:
			w.close()
			del w
		if g:
			self.graphWin.deleteLater()
			del self.graphWin
		self.summaryPlot=graphics.Plot()
		self.graphWin=self.centralWidget().addSubWindow(self.summaryPlot, subWinFlags)
		self.graphWin.setWindowTitle('Data Plot')
		self.graphWin.hide()
		
	def add_table(self):
			# Data Table (tabular view) window
		w=getattr(self, 'dataTable', False)
		if w:
			w.close()
			del w
			self.tableWin.deleteLater()
		self.dataTable=fileui.SummaryView(parent=self)
		self.tableWin=self.centralWidget().addSubWindow(self.dataTable, subWinFlags)
		self.tableWin.hide()
		
	def _init_instrument(self, soft=False):
		"""Called in a different thread. Need to recreate connection."""
		r=self.remote.copy()
		r.connect()
		return r.init_instrument(soft)
	def init_instrument(self, soft=False):
		#TODO: this scheme could be automated via a decorator: @thread 
		print 'Calling init_instrument in QThreadPool'
		r=widgets.RunMethod(self._init_instrument, soft)
		QtCore.QThreadPool.globalInstance().start(r)
		print 'active threads:', QtCore.QThreadPool.globalInstance().activeThreadCount(), QtCore.QThreadPool.globalInstance().maxThreadCount()
		
		

	@csutil.profile
	def setInstrument(self, remote, server=False):
		if server is not False:
			self.setServer(server)
		self.instrumentDock.hide()
		self.remote=remote
		name=self.remote['name']
		self.name=name
		print 'Setting remote',remote,self.remote,name
		self.setWindowTitle('misura Acquisition: %s (%s)' % (name, self.remote['comment']))
		pid='Instrument: '+self.name
		self.tasks.jobs(11,pid)
		QtGui.qApp.processEvents()
		if not self.fixedDoc and not self.server['isRunning'] and self.name!=self.server['lastInstrument']:
			print 'Init instrument'
			if self.remote.init_instrument is not None:
				self.tasks.job(0,pid,'Initializing instrument')
				QtGui.qApp.processEvents()
				# Async call of init_instrument
				self.init_instrument(soft=True) # soft: only if not already initialized
#				QtCore.QThreadPool.globalInstance().waitForDone()
				print 'active threads:', QtCore.QThreadPool.globalInstance().activeThreadCount(), QtCore.QThreadPool.globalInstance().maxThreadCount()
#				sleep(10)
#				self.remote.init_instrument()
		self.tasks.job(1,pid,'Preparing menus')
		self.myMenuBar.close()
		self.myMenuBar=MenuBar(server=self.server,parent=self)
		self.setMenuWidget(self.myMenuBar)
		print 'Done menubar'
		self.centralWidget().closeAllSubWindows()
		self.tasks.job(1,pid,'Controls')
		for tb in self.toolbars:
			self.removeToolBar(tb)
			tb.close()
			del tb
		self.toolbars=[]
		print 'Cleaned toolbars'
		self.controls=Controls(self.remote, parent=self)
		print 'Created controls'
		self.connect(self.controls, QtCore.SIGNAL('stopped_nosave()'),self.stopped_nosave)
		self.connect(self.controls, QtCore.SIGNAL('started()'),self.resetFileProxy)
		self.controls.mute=bool(self.fixedDoc)
		self.addToolBar(self.controls)
		self.toolbars.append(self.controls)
		print 'Done controls'
		self.tasks.job(-1,pid,'Status panel')
		
		
		self.logDock.hide()
		self.add_measure()
		
		self.tasks.job(-1,pid,'Frames')
		self.add_snapshots()
		
		self.tasks.job(-1,pid,'Graph')
		self.add_graph()
		
		self.tasks.job(-1,pid,'Data tree')
		self.add_sumtab()
		
		self.tasks.job(-1,pid,'Data Table')
		self.add_table()
		
		# Update Menu
		self.tasks.job(-1,pid,'Filling menus')
		print 'MENUBAR SET INSTRUMENT',remote
		self.myMenuBar.setInstrument(remote,server=self.server)
		self.myMenuBar.show()
		
		# Populate Cameras
		self.tasks.job(-1,pid,'Show cameras')
		paths=self.remote['devices']
		print 'setInstrument PATHS:',paths
		for p, (pic, win) in self.cameras.iteritems():
			pic.close()
			win.hide()
			win.deleteLater()
			
		self.cameras={}
		for path in paths:
			lst=self.server.searchPath(path[1])
			if not lst: continue
			obj=self.server.toPath(lst)
			if obj is None: continue
			role=obj['role'][self.name]
			if 'Camera' in obj['mro']:
				an=name.lower()
				if an=='post': an='post'
				if role=='NoRole': role='Camera'
				self.addCamera(obj, role, an)
		
		# Connect to "id" property
		self.tasks.job(-1,pid,'Document')
		self.idobj=widgets.ActiveObject(self.server, self.remote.measure, self.remote.measure.gete('id'))
		self.connect(self.idobj, QtCore.SIGNAL('changed()'), self.resetFileProxy)
		# Reset decoder and plot
		self.resetFileProxy()
		for obj1 in [self.dataTable,self.navigator,self.summaryPlot]:
			for obj2 in [self.dataTable,self.navigator,self.summaryPlot]:
				if obj1==obj2: continue
				p=functools.partial(obj2.hide_show,emit=False)
				self.connect(obj1,QtCore.SIGNAL('hide_show_col(QString,int)'),p)
				
		self.tasks.done(pid)

	def addCamera(self, obj, role='',analyzer='hsm'):
		#FIXME: old, nonsense
# 		obj['Analysis_instrument']=analyzer 
		pic=beholder.ViewerControl(obj,self.server, parent=self)
		pic.role=role
		win=self.centralWidget().addSubWindow(pic, subWinFlags)
		win.setWindowTitle('%s (%s)' %(roles.get(role, role), obj['name']))
		win.resize(640, 480)
		if not self.fixedDoc:
			win.show()
		else: 
			win.hide()
#		self.connect(pic, QtCore.SIGNAL('updatedROI()'), win.repaint)
		self.cameras[role]=(pic, win)
		
	retry=5
	def _resetFileProxy(self,retry=0):
		"""Resets acquired data widgets"""
		QtGui.qApp.processEvents()
		if self.doc:
			self.doc.close()
			self.doc=False
		doc=False
		fid=False
		if self.fixedDoc is not False:
			fid='fixedDoc'
			doc=self.fixedDoc
		elif self.server['initTest'] or self.server['closingTest']:
			self.tasks.jobs(0,'Test initialization')
			self.tasks.setFocus()
			print 'Waiting for initialization to complete...'
			QtGui.qApp.processEvents()
			sleep(.1)
			return self._resetFileProxy(retry=0)
		else:
			self.tasks.jobs(self.retry,'Waiting for data')
			self.tasks.done('Test initialization')
			self.tasks.job(retry,'Waiting for data')
			if retry>self.retry:
				self.tasks.done('Waiting for data')
				QtGui.QMessageBox.critical(self,self.mtr('Impossible to retrieve the ongoing test data'),
						self.mtr("""A communication error with the instrument does not allow to retrieve the ongoing test data.
						Please restart the client and/or stop the test."""))
				return False
			fid=self.remote.measure['uid']
			if fid=='':
				print 'no active test',fid
				self.tasks.done('Waiting for data')
				return False
			print 'resetFileProxy to live ',fid
			live=self.server.storage.test.live
			if not live.has_node('/conf'):
				live.load_conf()
			if not live.has_node('/conf'):
				print 'Conf node not found: acquisition has not been initialized.'
				self.tasks.job(0,'Waiting for data',
							'Conf node not found: acquisition has not been initialized.')
				self.tasks.done('Waiting for data')
				return False
			if fid==self.uid:
				print 'Measure id is still the same. Aborting resetFileProxy.'
				self.tasks.job(0,'Waiting for data',
							'Measure id is still the same. Aborting resetFileProxy.')
				self.tasks.done('Waiting for data')
				return False
			try:
#				live.reopen() # does not work when file grows...
				fp=RemoteFileProxy(live,conf=self.server,live=True)
				print fp.header()
				doc=filedata.MisuraDocument(proxy=fp)
				# Remember as the current uid
				self.uid=fid
			except:
				print 'RESETFILEPROXY error'
				print_exc()
				doc=False
				sleep(4)
				return self._resetFileProxy(retry=retry+1)
		self.tasks.done('Waiting for data')
		if doc is False:
			doc=filedata.MisuraDocument(root=self.server)	
		doc.up=True
		print 'RESETFILEPROXY',doc.filename,doc.data.keys(),doc.up
		self.set_doc(doc)
		
		
# 	@csutil.lockme
	def set_doc(self,doc):
		pid='Data display'
		self.tasks.jobs(10,pid)
		self.doc=doc
		self.tasks.job(-1,pid,'Setting document in live registry')
		registry.set_doc(doc)
		
		print 'snapshotsTable'
		self.tasks.job(-1,pid,'Sync snapshots with document')
		self.snapshotsTable.set_doc(doc)
		
		print 'summaryPlot'
		self.tasks.job(-1,pid,'Sync graph with document')
		self.summaryPlot.set_doc(doc)
		
		print 'navigator'
		self.tasks.job(-1,pid,'Sync document tree')
		self.navigator.set_doc(doc)

		print 'dataTable'
		self.tasks.job(-1,pid,'Sync data table')
		self.dataTable.set_doc(doc)
		print 'connect'
		self.connect(self.snapshotsTable,QtCore.SIGNAL('set_time(float)'),self.summaryPlot.set_time)
		self.connect(self.snapshotsTable,QtCore.SIGNAL('set_time(float)'),self.navigator.set_time)
		self.connect(self.summaryPlot,QtCore.SIGNAL('move_line(float)'),self.snapshotsTable.set_time)
		self.tasks.done(pid)

# 	@csutil.profile
	@csutil.unlockme
	def resetFileProxy(self,*a,**k):
		"""Locked version of resetFileProxy"""
		if not self._lock.acquire(False):
			print 'ANOTHER RESETFILEPROXY IS RUNNING!'
			return
		registry.toggle_run(False)
		r=False
		try:
			r=self._resetFileProxy(*a,**k)
		except:
			print_exc()
		print 'Restarting registry'
		registry.toggle_run(True)
		self.tasks.done('Waiting for data')
		self.tasks.hide()
		return r

	def createAction(self, text, slot=False, shortcut=False,  icon=False, tip=False, checkable=False, signal="triggered()"):
		action=QtGui.QAction(text, self)
		if icon: action.setIcon(QtGui.QIcon(":%s.png" % icon))
		if shortcut: action.setShortcut(shortcut)
		if tip:
			action.setToolTip(tip)
			action.setStatusTip(tip)
		if slot: self.connect(action, QtCore.SIGNAL("signal"), slot)
		if checkable: action.setCheckable(True)
		return action

	def addActions(self, target, actions):
		for action in actions:
			if actions is None:
				target.addSeparator()
			else:
				target.addAction(action)
	
	def delayed_start(self):
		"""Configure delayed start"""
		#TODO: disable the menu action!
		if self.server['isRunning']:
			QtGui.QMessageBox.warning(self, "Already running", "Cannot set a delayed start. \nInstrument is already running.")
			return False
		self.delayed=DelayedStart(self.server)
		self.delayed.show()
		

	###########
	### Post-analysis
	###########
	def showIDB(self):
		"""Shows remote database selection window."""
		self.idb=DatabaseWidget(self.server.storage,self)
		win=self.centralWidget().addSubWindow(self.idb)
		self.connect(self.idb,QtCore.SIGNAL('selectedUid(QString)'),self.post_uid)
		win.show()

	def showDB3(self):
		"""Shows selection windows for db3."""
		self.db3Dia=m3db.TestDialog(self)
		self.db3Dia.importAllFields=True
		win=self.centralWidget().addSubWindow(self.db3Dia)
		win.show()
		self.connect(self.db3Dia, QtCore.SIGNAL('imported(QString)'), self.post_file)

	def openFile(self):
		"""Selects misura HDF file for post-analysis"""
		path=QtGui.QFileDialog.getOpenFileName(self,"Select misura File","C:\\")
		if not path: return
		self.post_file(path)

	def post_file(self, filename):
		"""Slot called when a misura file is opened for post-analysis."""
		#TODO: migrate to the new SharedFile interface
		filename=str(filename)
		f=tables.openFile(filename,'r')
		uid=str(f.root.summary.attrs.uid)
		f.close()
		r=self.post_uid(uid)
		if not r:
			upthread=UploadThread(self.server.storage,filename,parent=self)
			upthread.show()
			upthread.start()
			self.reinit_post=functools.partial(self.post_uid,filename)
			self.connect(upthread,QtCore.SIGNAL('ok()'),self.reinit_post)
			return False
		
	def post_uid(self,uid):
		uid=str(uid)
		r=self.server.storage.searchUID(uid)
		print 'SEARCH UID',r
		if not r: 
			return False
		self.remote.init_uid(uid)
		# Attiva lo streaming se è spento
		for cam, win in self.cameras.itervalues():
			cam.toggle(1)
		return True

