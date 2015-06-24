#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools
from time import sleep
import threading
from traceback import  format_exc
import os
import sys
import tables

from misura.canon.logger import Log as logging
from misura.canon import csutil

from .. import _
from ..live import registry
from .. import network
from ..network import TransferThread
from .. import widgets, beholder
from .. import fileui, filedata, navigator
from ..misura3 import m3db
from .. import connection
from ..clientconf import confdb
from ..confwidget import RecentWidget
from .menubar import MenuBar
from .selector import InstrumentSelector
from .measureinfo import MeasureInfo
from .controls import Controls, MotionControls
from .delay import DelayedStart 

# Synchronization stuff
from .. import sync

from .. import graphics
from ..database import UploadThread
from ..filedata import RemoteFileProxy 



from PyQt4 import QtGui, QtCore

subWinFlags=QtCore.Qt.CustomizeWindowHint|QtCore.Qt.WindowTitleHint|QtCore.Qt.WindowMinMaxButtonsHint

roles={'motorBase':'Base Position', 'motorHeight':'Height Position',
                'motorRight':'Right Position', 'motorLeft':'Left Position',
                'focus':'Focus adjust', 'motor':'Position', 'camera':'Main',
                'cameraBase':'Base', 'cameraHeight':'Height', 'cameraRight':'Right',
                'cameraLeft':'Left', 'force':'Weight',
                'angleHeight':'Height Inclination','angleBase':'Base Inclination',
                'angleRight':'Right Inclination','angleLeft':'LeftInclination'}

class MainWindow(QtGui.QMainWindow):
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
		self._lock=threading.Lock()
		self.cameras={}
		self.toolbars=[]
		self.fixedDoc=doc
		self.server=False
		self.area=QtGui.QMdiArea()
		self.setCentralWidget(self.area)
		self.setMinimumSize(800,600)
		self.setWindowTitle(_('Misura Live'))
		self.myMenuBar=MenuBar(parent=self)
		self.setMenuWidget(self.myMenuBar)
		self.connect(network.manager, QtCore.SIGNAL('connected()'), self.setServer)	
		self.add_server_selector()
		self.reset_proxy_timer=QtCore.QTimer(parent=self)
		self.reset_proxy_timer.setSingleShot(True)
		self.reset_proxy_timer.setInterval(500)
		self.connect(self.reset_proxy_timer, QtCore.SIGNAL('timeout()'), self._resetFileProxy)

	def add_server_selector(self):
		"""Server selector dock widget"""
		self.serverDock=QtGui.QDockWidget(self.centralWidget())
# 		self.serverSelector=connection.ServerSelector(self.serverDock)
		self.serverSelector=RecentWidget(confdb,'server',self.serverDock)
		self.connect(self.serverSelector,self.serverSelector.sig_select,self.set_addr)
		self.serverDock.setWindowTitle(self.serverSelector.label)
		self.serverDock.setWidget(self.serverSelector)
		self.addDockWidget(QtCore.Qt.TopDockWidgetArea,self.serverDock)
		
	def rem(self, d, w=False):
		"""Removes a dock widget by name"""
		d=getattr(self, d, False)
		if not d: return
		self.removeDockWidget(d)
		d.deleteLater()
		if not w: return
		w=getattr(self, w,False)
		if w: w.deleteLater()
				
	def set_addr(self,addr):
		"""Open server by address"""
		s=connection.addrConnection(addr)
		network.manager.set_remote(s)
		registry.toggle_run(False)
		registry.set_manager(network.manager)
		registry.toggle_run(True)
		self.setServer(s)
	_blockResetFileProxy=False
	def setServer(self, server=False):
		self._blockResetFileProxy=True
		logging.debug('%s %s', 'Setting server to', server)
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
			self.logDock.setWidget(connection.LiveLog(self.logDock))		
		self.addDockWidget(QtCore.Qt.BottomDockWidgetArea,self.logDock)
		
		self.setMenuBar(self.myMenuBar)
		
		
		self.rem('instrumentDock')
		self.instrumentDock=QtGui.QDockWidget(self.centralWidget())
		self.instrumentSelector=InstrumentSelector(self,self.setInstrument)
		self.instrumentDock.setWidget(self.instrumentSelector)
		self.addDockWidget(QtCore.Qt.TopDockWidgetArea,self.instrumentDock)
		logging.debug('%s', self.server.describe())
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
		logging.debug('%s', 'Calling init_instrument in QThreadPool')
		r=widgets.RunMethod(self._init_instrument, soft)
		r.pid='Instrument initialization '
		QtCore.QThreadPool.globalInstance().start(r)
		logging.debug('%s %s %s', 'active threads:', QtCore.QThreadPool.globalInstance().activeThreadCount(), QtCore.QThreadPool.globalInstance().maxThreadCount())
		
#	@csutil.profile
	def setInstrument(self, remote, server=False):
		if server is not False:
			self.setServer(server)
		self._blockResetFileProxy=True
		self.instrumentDock.hide()
		self.remote=remote
		name=self.remote['devpath']
		self.name=name
		logging.debug('Setting remote %s %s %s', remote, self.remote, name)
		self.setWindowTitle('misura Acquisition: %s (%s)' % (name, self.remote['comment']))
		pid='Instrument: '+self.name
		self.tasks.jobs(11,pid)
		QtGui.qApp.processEvents()
		if not self.fixedDoc and not self.server['isRunning'] and self.name!=self.server['lastInstrument']:
			logging.debug('Init instrument')
			if self.remote.init_instrument is not None:
				self.tasks.job(0,pid,'Initializing instrument')
				QtGui.qApp.processEvents()
				# Async call of init_instrument
				self.init_instrument(soft=True) # soft: only if not already initialized
#				QtCore.QThreadPool.globalInstance().waitForDone()
				logging.debug('%s %s %s', 'active threads:', QtCore.QThreadPool.globalInstance().activeThreadCount(), QtCore.QThreadPool.globalInstance().maxThreadCount())
#				sleep(10)
#				self.remote.init_instrument()
		self.tasks.job(1,pid,'Preparing menus')
		self.myMenuBar.close()
		self.myMenuBar=MenuBar(server=self.server,parent=self)
		self.setMenuWidget(self.myMenuBar)
		logging.debug('%s', 'Done menubar')
		
		# Close cameras
		logging.debug('Defined cameras', self.cameras)
		for p, (pic, win) in self.cameras.iteritems():
			logging.debug('deleting cameras', p, pic, win)
			pic.close()
			win.hide()
			win.close()
			win.deleteLater()
		self.cameras={}
		# Remove any remaining subwindow
		self.centralWidget().closeAllSubWindows()
	
	
		self.tasks.job(1,pid,'Controls')
		for tb in self.toolbars:
			self.removeToolBar(tb)
			tb.close()
			del tb
		self.toolbars=[]
		logging.debug('%s', 'Cleaned toolbars')
		self.controls=Controls(self.remote, parent=self)
		logging.debug('%s', 'Created controls')
		self.controls.stopped_nosave.connect(self.stopped_nosave)
		self.controls.stopped.connect(self.stopped)
		self.controls.started.connect(self.resetFileProxy)
		self.controls.mute=bool(self.fixedDoc)
		self.addToolBar(self.controls)
		self.toolbars.append(self.controls)
		logging.debug('%s', 'Done controls')
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
		logging.debug('%s %s', 'MENUBAR SET INSTRUMENT', remote)
		self.myMenuBar.setInstrument(remote,server=self.server)
		self.myMenuBar.show()
		
		# Populate Cameras
		self.tasks.job(-1,pid,'Show cameras')
		paths=self.remote['devices']
		logging.debug('%s %s', 'setInstrument PATHS:', paths)
		
		for path in paths:
			lst=self.server.searchPath(path[1])
			if not lst: continue
			obj=self.server.toPath(lst)
			if obj is None: continue
# 			role=obj['role'][self.name]
			role='NoRole'
			if 'Camera' in obj['mro']:
				an=name.lower()
				if an=='post': an='post'
				if role=='NoRole': role='Camera'
				self.addCamera(obj, role, an)
		
		# Add motion controls toolbar
		if not self.fixedDoc:
			self.mcontrols=MotionControls(self.remote, parent=self)
			self.addToolBar(QtCore.Qt.BottomToolBarArea, self.mcontrols)
			self.toolbars.append(self.mcontrols)
		
		# Connect to "id" property
		self.tasks.job(-1,pid,'Document')
		self.idobj=widgets.ActiveObject(self.server, self.remote.measure, self.remote.measure.gete('id'), parent=self)
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
		self.cameras[obj['fullpath']]=(pic, win)
		
		
# 	@csutil.lockme
	def set_doc(self,doc):
		pid='Data display'
		self.tasks.jobs(10,pid)
		self.doc=doc
		self.tasks.job(-1,pid,'Setting document in live registry')
		registry.set_doc(doc)
		
		logging.debug('%s', 'snapshotsTable')
		self.tasks.job(-1,pid,'Sync snapshots with document')
		self.snapshotsTable.set_doc(doc)
		
		logging.debug('%s', 'summaryPlot')
		self.tasks.job(-1,pid,'Sync graph with document')
		self.summaryPlot.set_doc(doc)
		
		logging.debug('%s', 'navigator')
		self.tasks.job(-1,pid,'Sync document tree')
		self.navigator.set_doc(doc)

		logging.debug('%s', 'dataTable')
		self.tasks.job(-1,pid,'Sync data table')
		self.dataTable.set_doc(doc)
		logging.debug('%s', 'connect')
		self.connect(self.snapshotsTable,QtCore.SIGNAL('set_time(float)'),self.summaryPlot.set_time)
		self.connect(self.snapshotsTable,QtCore.SIGNAL('set_time(float)'),self.navigator.set_time)
		self.connect(self.summaryPlot,QtCore.SIGNAL('move_line(float)'),self.snapshotsTable.set_time)
		self.tasks.done(pid)
		
	max_retry=10
	def _resetFileProxy(self,retry=0, recursion=0):
		"""Resets acquired data widgets"""
		if self._blockResetFileProxy:
			return False
		QtGui.qApp.processEvents()
		if self.doc:
			self.doc.close()
			self.doc=False
		doc=False
		fid=False
		if recursion>sys.getrecursionlimit()-10:
			return False
		if self.fixedDoc is not False:
			fid='fixedDoc'
			doc=self.fixedDoc
		elif self.server['initTest'] or self.server['closingTest']:
			self.tasks.jobs(0,'Test initialization')
			self.tasks.setFocus()
			logging.debug('%s', 'Waiting for initialization to complete...')
			QtGui.qApp.processEvents()
			sleep(0.2)
			return self._resetFileProxy(retry=0, recursion=recursion+1)
		else:
			if not self.server['isRunning']: 
				retry=5
			self.tasks.jobs(self.max_retry,'Waiting for data')
			self.tasks.done('Test initialization')
			self.tasks.job(retry,'Waiting for data')
			QtGui.qApp.processEvents()
			if retry<5:
				sleep(retry/2.)
				return self._resetFileProxy(retry=retry+1, recursion=recursion+1)
			if retry>self.max_retry:
				self.tasks.done('Waiting for data')
				QtGui.QMessageBox.critical(self,_('Impossible to retrieve the ongoing test data'),
						_("""A communication error with the instrument does not allow to retrieve the ongoing test data.
						Please restart the client and/or stop the test."""))
				return False
			fid=self.remote.measure['uid']
			if fid=='':
				logging.debug('%s %s', 'no active test', fid)
				self.tasks.done('Waiting for data')
				return False
			logging.debug('%s %s', 'resetFileProxy to live ', fid)
			live_uid=self.server.storage.test.live.get_uid()
			if not live_uid:
				return False
			live=getattr(self.server.storage.test,live_uid)
			if not live.has_node('/conf'):
				live.load_conf()
			if not live.has_node('/conf'):
				logging.debug('%s', 'Conf node not found: acquisition has not been initialized.')
				self.tasks.job(0,'Waiting for data',
							'Conf node not found: acquisition has not been initialized.')
				self.tasks.done('Waiting for data')
				return False
			if fid==self.uid:
				logging.debug('%s', 'Measure id is still the same. Aborting resetFileProxy.')
				self.tasks.job(0,'Waiting for data',
							'Measure id is still the same. Aborting resetFileProxy.')
				self.tasks.done('Waiting for data')
				return False
			try:
#				live.reopen() # does not work when file grows...
				fp=RemoteFileProxy(live,conf=self.server,live=True)
				logging.debug('%s', fp.header())
				doc=filedata.MisuraDocument(proxy=fp)
				# Remember as the current uid
				self.uid=fid
			except:
				logging.debug('RESETFILEPROXY error')
				logging.debug(format_exc())
				doc=False
				sleep(4)
				return self._resetFileProxy(retry=retry+1, recursion=recursion+1)
		self.tasks.done('Waiting for data')
		if doc is False:
			doc=filedata.MisuraDocument(root=self.server)	
		doc.up=True
		logging.debug('%s %s %s %s', 'RESETFILEPROXY', doc.filename, doc.data.keys(), doc.up)
		self.set_doc(doc)
	
	@csutil.unlockme
	def resetFileProxy(self,*a,**k):
		"""Locked version of resetFileProxy"""
		if not self._lock.acquire(False):
			logging.debug('ANOTHER RESETFILEPROXY IS RUNNING!')
			return
		self._blockResetFileProxy=False
		logging.debug('MainWindow.resetFileProxy: Stopping registry')
		registry.toggle_run(False)
		r=False
		try:
			r=self._resetFileProxy(*a,**k)
		except:
			logging.debug('%s', format_exc())
		self._finishFileProxy()
		return r
		
	def _finishFileProxy(self):
		logging.debug('%s', 'MainWindow.resetFileProxy: Restarting registry')
		registry.toggle_run(True)
		self.tasks.done('Waiting for data')
		self.tasks.hide()
	

	###########
	### Start/Stop utilities
	###########
	
	def delayed_start(self):
		"""Configure delayed start"""
		#TODO: disable the menu action!
		if self.server['isRunning']:
			QtGui.QMessageBox.warning(self, "Already running", "Cannot set a delayed start. \nInstrument is already running.")
			return False
		self.delayed=DelayedStart(self.server)
		self.delayed.show()
		
	def stopped_nosave(self):
		"""Reset the instrument, completely discarding acquired data and remote file proxy"""
		logging.debug('%s', "STOPPED_NOSAVE")
		#TODO: reset ops should be performed server-side
		self.remote.measure['uid']=''
		self.resetFileProxy()
		
	def stopped(self):
		"""Offer option to download the remote file"""
		#HTTPS data url
		uid=self.remote.measure['uid']
		dbpath=confdb['database']
		# NO db: ask to specify custom location
		if not os.path.exists(dbpath):
			logging.debug('%s %s', 'DATABASE PATH DOES NOT EXIST', dbpath)
			dbpath=False
			outfile=QtGui.QFileDialog.getSaveFileName(self,	_("Download finished test as"))
			outfile=str(outfile)
			if not len(outfile):
				return False
			auto=True
		else:
			auto=confdb['autodownload']
			outfile=False
		# Ask if it's not automatic
		if not auto:
			auto=QtGui.QMessageBox.question(self,_("Download finished test?"),
									_("Would you like to save the finished test?"))
			if auto!=QtGui.QMessageBox.Ok:
				return False	
		#TODO: Must wait that current file is closed!!!
		# Must download
		sy=TransferThread(outfile=outfile,uid=uid,server=self.server,dbpath=dbpath)
		sy.set_tasks(self.tasks)
		sy.start()
		# Keep a reference
		self._download_thread=sy

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
		logging.debug('%s %s', 'SEARCH UID', r)
		if not r: 
			return False
		self.remote.init_uid(uid)
		# Attiva lo streaming se è spento
		for cam, win in self.cameras.itervalues():
			cam.toggle(1)
		return True

