#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Database synchronization service and widget"""
import os
import logging
from time import sleep
from traceback import format_exc

from .. import _
from ..clientconf import confdb
from ...canon import indexer
from ..network import TransferThread, remote_dbdir

from PyQt4 import QtCore, QtGui, QtSql

record_length=len(indexer.indexer.testColumn)

class StorageSync(object):
	"""Storage synchronization utilities"""
	chunk=25
	"""Max UID collect request"""
	server=False
	serial=False
	
	def __init__(self,transfer=False):
		self.transfer=transfer
		"""Object implementing a download_url(url,outfile) method"""
		
	def set_server(self,server):
		"""Sets remote server towards which to run the synchronization service"""
		self.server=server
		self.remote_dbdir=remote_dbdir(server)
		"""Remote db directory"""
		self.serial=self.server['eq_sn']
		"""Server serial number"""	
		self.tot=self.server.storage.get_len()
		if self.tot is None: self.tot=0
		self.start=self.tot-self.chunk
		if self.start<0: self.start=0
		return True
	
	def set_dbpath(self,dbpath):
		"""Set the local database path for storage synchronization"""
		if not dbpath:
			dbpath=confdb['database']
		self.dbpath=dbpath
		if not os.path.exists(self.dbpath):
			logging.debug('%s %s', 'Database path does not exist!', self.dbpath)
			return False		
		self.db=indexer.Indexer(self.dbpath)	
		return True	
	
	@property
	def dbdir(self):
		dbdir=os.path.join(os.path.dirname(self.dbpath),self.serial)
		if not os.path.exists(dbdir):
			os.makedirs(dbdir)
		return dbdir
		
		
	def prepare(self,dbpath=False,server=False):
		"""Open database and prepare operations"""
		if not self.set_dbpath(dbpath):
			return False
		if server:
			self.set_server(server)

		return True

	def has_uid(self,uid, tname):
		"""Check if `uid` is in table `tname`"""
		r=self.db.execute_fetchall("SELECT 1 from {} where uid='{}'".format(tname,unicode(uid)))
		return len(r)
		
	def rem_uid(self,uid,tname):
		"""Remove `uid` from table `tname`"""
		self.db.execute("DELETE from {} where uid='{}'".format(tname,uid))
		logging.debug('removed uid %s %s',tname,uid)
	
	def add_record(self,record, tname):
		"""Adds `record` list to table `tname`"""
		v=('?,'*len(record))[:-1]
		self.db.execute("INSERT INTO {} VALUES ({})".format(tname,v),record)
		logging.debug('added record %s %s',tname,record)
	
	def queue_record(self,record):
		"""Approve `record` for download."""
		# Check if previously approved (exit) or already excluded (remove!)
		uid=record[2]
		if self.has_uid(uid,'sync_approve'):
			self.rem_uid(uid,'sync_approve')
		
		if self.has_uid(uid, 'sync_exclude'):
			logging.debug('%s %s', 'Record was excluded. Enabling.', record)
			self.rem_uid(uid,'sync_exclude')
			
		if self.has_uid(uid, 'sync_error'):
			logging.debug('%s %s', 'Retrying: ', record)
			self.rem_uid(uid,'sync_error')
			
		if self.has_uid(uid,'sync_queue'):
			logging.debug('%s %s', 'Record already queued', record)
			return False
		
		if len(record)>record_length:
			record=record[:record_length]
		self.add_record(record,'sync_queue')
		return True
	
	def exclude_record(self,record):
		"""Exclude `record` for download."""
		# Check if previously approved (remove!) or already excluded (exit)
		uid=record[2]
		if self.has_uid(uid, 'sync_queue'):
			logging.debug('%s %s', 'Record was queued. Enabling.', record)
			self.rem_uid(uid,'sync_queue')
			
		if self.has_uid(uid,'sync_approve'):
			self.rem_uid(uid,'sync_approve')
			
		if self.has_uid(uid,'sync_error'):
			self.rem_uid(uid,'sync_error')
			
		if self.has_uid(uid,'sync_exclude'):
			logging.debug('%s %s', 'Record already excluded', record)
			return False
		if len(record)>record_length:
			record=record[:record_length]
		self.add_record(record,'sync_exclude')
		return True
		
	def collect(self,server=False):
		"""Scan through a chunk of rows and check if they exist in local archive."""
		# Restart from zero
		if not server:
			server=self.server
		if self.start==self.tot:
			self.tot=self.server.storage.get_len()
			self.start=-60 
		# skip next iterations
		if self.start<0:
			self.start+=1
			return 0
		end=self.start+self.chunk
		if end>=self.tot: end=self.tot
		lst=server.storage.list_tests(self.start,self.start+25)[::-1]
		i=0
		for record in lst:
			uid=record[2]
			if self.has_uid(uid,'sync_queue'):
				continue
			if self.has_uid(uid,'sync_exclude'):
				continue
			if self.has_uid(uid,'sync_error'):
				continue
			if self.has_uid(uid,'sync_approve'):
				continue
			r=self.db.searchUID(uid,full=True)
			if r and os.path.exists(r[0]):
				continue
			self.add_record(record,'sync_approve')
			i+=1
		self.start=end
		return i
	
	def __len__(self):
		"""Returns the length of the approval queue"""
		if not self.server:
			return 0
		return self.db.tab_len('sync_approve')
		
	def download(self):
		"""Search for the next file to download"""
		record=self.db.execute_fetchone("SELECT * from sync_queue where serial='{}'".format(self.serial))
		if not record:
			# Nothing to download
			return False
# 		record=record[0]
		r=False
		error='Unknown error'
		try:
			r=self.download_record(record)
		except:
			error=format_exc()
		if not r: 
			logging.info('Failed test file download %s: \n%s',record,error)
			error=list(record)+[error]
			self.add_record(error,'sync_error')
		self.rem_uid(record[2],'sync_queue')
		return r
		
	def download_record(self,record):
		"""Start the chunked download of a record"""
		logging.debug('%s %s %s', 'download_record', record,self.remote_dbdir)
		remote_path=record[0]
		p=remote_path.replace(self.remote_dbdir,'').split('/')
		print 'record path',p
		fn=p.pop(-1)
		print 'record filename',fn
		outfile=os.path.join(self.dbdir,fn)
		d='/'+os.path.join(*p)
		url=self.server.data_addr+d+'/'+fn
		r=self.transfer.download_url(url,outfile)
		self.db.appendFile(outfile)
		return r
	
	def loop(self,server=False):
		"""Inner synchronization loop. 
		If called from a different thread, can pass optional `server` 
		in order to avoid multithreading reconnection issues."""
		if not server:
			server=self.server
		if server['isRunning']:
			return 0
		n=self.collect(server)
		# Download next file
		if not server['isRunning']:
			self.download()
		return n
		
	
class SyncTable(QtGui.QTableView):
	"""Table showing queued sync files, allowing the user to interact with them"""
	length=0
	queueRecord=QtCore.pyqtSignal(object)
	excludeRecord=QtCore.pyqtSignal(object)
	def __init__(self,dbpath,table_name,parent=None):
		super(SyncTable,self).__init__(parent)
		db=QtSql.QSqlDatabase.addDatabase('QSQLITE')
		self.dbpath=dbpath
		db.setDatabaseName(dbpath)
		model=QtSql.QSqlTableModel()
		model.setTable(table_name)
		model.select()
		self.setModel(model)
		for i in (0,6,9,11):
			self.hideColumn(i)
		self.selection=QtGui.QItemSelectionModel(self.model())
		self.setSelectionModel(self.selection)
		self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.menu=QtGui.QMenu(self)
		if table_name.endswith('_approve'):
			self.menu.addAction(_('Download'),self.enqueue)
			self.menu.addAction(_('Ignore'),self.exclude)
		elif table_name.endswith('_queue'):
			self.menu.addAction(_('Ignore'),self.exclude)
		elif table_name.endswith('_exclude'):
			self.menu.addAction(_('Download'),self.enqueue)
		elif table_name.endswith('_error'):
			self.menu.addAction(_('Retry'),self.enqueue)
			self.menu.addAction(_('Ignore'),self.exclude)
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
		
	def showMenu(self, pt):
		self.menu.popup(self.mapToGlobal(pt))
		
	def showEvent(self,ev):
		"""Automatically switch to appropriate queue when showed"""
		self.model().select()
		return super(SyncTable,self).showEvent(ev)	
		
	def __len__(self):
		"""Returns the number of rows of the current table for the connected server serial"""
		n=self.model().rowCount()
		if n!=self.length:
			self.model().select()
			self.length=n
		return  n
	
	def iter_selected(self):
		"""Iterate over selected rows returning their corresponding sql record"""
		column_count=self.model().columnCount()
		for row in self.selectionModel().selectedRows():
			r=[]
			row=row.row()
			for i in range(column_count):
				idx=self.model().index(row,i)
				r.append(self.model().data(idx))
			yield r
					
	def enqueue(self):
		"""Promote selection to sync_queue table"""
		for record in self.iter_selected():
			self.queueRecord.emit(record)
		self.model().select()
	
	def exclude(self):
		"""Move selection to sync_exclude table"""
		for record in self.iter_selected():
			self.excludeRecord.emit(record)
		self.model().select()
		

class SyncWidget(QtGui.QTabWidget):
	"""Allows the user to control sync behavior."""
	ch=QtCore.pyqtSignal()
	dbpath=False
	def __init__(self,parent=None):
		super(SyncWidget,self).__init__(parent)
		self.transfer=TransferThread(self)
		# Set local tasks manager
		if parent:
			self.transfer.set_tasks(parent.tasks)
		self.storage_sync=StorageSync(self.transfer)
		dbpath=confdb['database']
		#Create if missing
		try:
			db=indexer.Indexer(dbpath)
			db.close()
		except:
			logging.info('Cannot set local db for storage sync \n%',format_exc())
			return
		self.dbpath=dbpath
		
		
		self.tab_approve=self.add_sync_table('sync_approve',_('Waiting approval'))
		
		self.tab_queue=self.add_sync_table('sync_queue',_('Download queue'))
		
		self.tab_error=self.add_sync_table('sync_error',_('Errors'))
				
		self.tab_exclude=self.add_sync_table('sync_exclude',_('Ignored'))
		
	def add_sync_table(self,table_name,title):
		"""Create a new SyncTable, add corresponding tab and connects relevant signals"""
		obj=SyncTable(self.dbpath,table_name,parent=self)
		self.addTab(obj,title)
		obj.queueRecord.connect(self.storage_sync.queue_record)
		obj.excludeRecord.connect(self.storage_sync.exclude_record)
		return obj
		
		
	def set_server(self,server):
		if not self.dbpath:
			logging.debug('SyncWidget.set_server: No database path set %s',self.dbpath)
			return
		self.storage_sync.prepare(self.dbpath,server)
		serial="serial='{}'".format(server['eq_sn'])
		self.tab_approve.model().setFilter(serial)
		self.tab_queue.model().setFilter(serial)
		self.tab_error.model().setFilter(serial)
		self.tab_exclude.model().setFilter(serial)
		
		
	def loop(self,server=False):
		"""Do one collect/download loop.
		Optionally pass `server` if calling from a different thread."""
		if not self.dbpath:
			logging.debug('SyncWidget.loop: No database path set %s',self.dbpath)
			return False
		self.storage_sync.set_dbpath(self.dbpath)
		if not self.storage_sync.server:
			logging.debug('No server set')
			return False
		n= self.storage_sync.loop(server)
		if n:
			self.ch.emit()
	
	def __len__(self):
		"""Returns the length of the approval queue"""
		if not self.dbpath:
			return 0
		n = len(self.tab_approve)
		return n
	
	def showEvent(self,ev):
		"""Automatically switch to appropriate queue when showed"""
		r=super(SyncWidget,self).showEvent(ev)
		if not self.dbpath:
			return r
		if len(self.tab_approve):
			if self.currentIndex()!=0:
				self.setCurrentIndex(0)
		elif len(self.tab_error):
			if self.currentIndex()!=2:
				self.setCurrentIndex(2)
		return r
		

