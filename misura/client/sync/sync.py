#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Database synchronization service and widget"""
import os
import logging
from time import sleep
from .. import _
from ..clientconf import confdb
from ...canon import indexer
from ..network import TransferThread, remote_dbdir

from PyQt4 import QtCore, QtGui, QtSql


class StorageSync(object):
	"""Synchronization utilities"""
	chunk=25
	"""Max UID collect request"""
	server=False
	
	def __init__(self,transfer=False):
		self.transfer=transfer
		"""Object implementing a download_url(url,outfile) method"""
		
	def set_server(self,server):
		self.server=server
		self.remote_dbdir=remote_dbdir(server)
		"""Remote db directory"""
		self.serial=self.server['eq_sn']
		"""Server serial number"""	
		self.tot=self.server.storage.get_len() #TODO: recheck and put latest on top
		self.start=self.tot-self.chunk
		if self.start<0: self.start=0
		return True
		
	def set_dbpath(self,dbpath):
		if not dbpath:
			dbpath=confdb['database']
		self.dbpath=dbpath
		if not os.path.exists(self.dbpath):
			logging.debug('%s %s', 'Database path does not exist!', self.dbpath)
			return False		
		self.dbdir=os.path.dirname(self.dbpath)
		self.db=indexer.Indexer(self.dbpath)	
		return True	
		
	def prepare(self,dbpath=False,server=False):
		"""Open database and prepare operations"""
		if server:
			self.set_server(server)
		if not self.set_dbpath(dbpath):
			return False
		return True
	

	def has_uid(self,uid, tname):
		"""Check if `uid` is in table `tname`"""
		r=self.db.execute_fetchall("SELECT 1 from {} where uid='{}'".format(tname,uid))
		return len(r)
		
	def rem_uid(self,uid,tname):
		"""Remove `uid` from table `tname`"""
		self.db.execute("DELETE from {} where uid='{}'".format(tname,uid))
	
	def add_record(self,record, tname):
		v=('?,'*len(record))[:-1]
		self.db.execute("INSERT INTO {} VALUES ({})".format(tname,v),record)
	
	def queue_record(self,record):
		"""Approve `record` for download."""
		# Check if previously approved (exit) or already excluded (remove!)
		uid=record[2]
		if self.has_uid(uid,'sync_approve'):
			self.rem_uid(uid,'sync_approve')
		
		if self.has_uid(uid, 'sync_exclude'):
			logging.debug('%s %s', 'Record was excluded. Enabling.', record)
			self.rem_uid(uid,'sync_exclude')
			
		if self.has_uid(uid,'sync_queue'):
			logging.debug('%s %s', 'Record already queued', record)
			return False

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
			
		if self.has_uid(uid,'sync_exclude'):
			logging.debug('%s %s', 'Record already excluded', record)
			return False

		self.add_record(record,'sync_exclude')
		return True
		
	def collect(self):
		"""Scan through a chunk of rows and check if they exist in local archive."""
		end=self.start+self.chunk
		if end>=self.tot: end=self.tot
		lst=self.server.storage.list_tests(self.start,self.start+25)[::-1]
		i=0
		for t in lst:
			uid=t[2]
			if self.has_uid(uid,'sync_queue'):
				continue
			if self.has_uid(uid,'sync_exclude'):
				continue
			if self.has_uid(uid,'sync_approve'):
				continue
			r=self.db.searchUID(t[2],full=True)
			if r and os.path.exists(r[0]):
				continue
			self.add_record(t,'sync_approve')
			i+=1
		self.start=end
		return i
		
	def tab_len(self,table_name):
		"""Returns length of a table"""
		if not self.db:
			return 0
		r= self.db.execute_fetchone('SELECT COUNT(*) from {}'.format(table_name))
		if not r:
			return 0
		return r[0]
	
	def __len__(self):
		"""Returns the length of the approval queue"""
		if not self.server:
			return 0
		return self.tab_len('sync_approve')
		
	def download(self):
		"""Search for the next file to download"""
		record=self.db.execute_fetchone('SELECT * from sync_queue')
		if not record:
			# Nothing to download
			return False
# 		record=record[0]
		r=self.download_record(record)
		if not r: 
			logging.error('Failed download %s',record)
			return False
		self.db.execute("DELETE from sync_queue WHERE file='{}'".format(record[0]))
		return True
		
	def download_record(self,record):
		"""Start the chunked download of a record"""
		logging.debug('%s %s %s', 'download_record', record,self.remote_dbdir)
		p=record[0].replace(self.remote_dbdir,'').split('/')
		print 'record path',p
		fn=p.pop(-1)
		print 'record filename',fn
		d='/'+os.path.join(*p)
		#TODO: give unique name
		outfile=os.path.join(self.dbdir,fn)
		url=self.server.data_addr+d+'/'+fn
		r=self.transfer.download_url(url,outfile)
		self.db.appendFile(outfile)
		return r
	
	def loop(self):
		"""Inner synchronization loop"""
		if self.server['isRunning']:
			sleep(1)
		n=self.collect()
		# Download next file
		if not self.server['isRunning']:
			self.download()
		return n
		
	
class SyncTable(QtGui.QTableView):
	"""Table showing queued sync files, allowing the user to interact with them"""
	def __init__(self,dbpath,table_name,parent=None):
		super(SyncTable,self).__init__(parent)
		db=QtSql.QSqlDatabase.addDatabase('QSQLITE')
		self.dbpath=dbpath
		db.setDatabaseName(dbpath)
		model=QtSql.QSqlTableModel()
		model.setTable(table_name)
		model.select()
		self.setModel(model)
		self.selection=QtGui.QItemSelectionModel(self.model())
		self.setSelectionModel(self.selection)
		self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.menu=QtGui.QMenu(self)
		if table_name.endswith('_approve'):
			self.menu.addAction(_('Enqueue'),self.enqueue)
			self.menu.addAction(_('Exclude'),self.exclude)
		elif table_name.endswith('_queue'):
			self.menu.addAction(_('Exclude'),self.exclude)
		elif table_name.endswith('_exclude'):
			self.menu.addAction(_('Enqueue'),self.enqueue)
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
		
	def showMenu(self, pt):
		self.menu.popup(self.mapToGlobal(pt))
		
	def iter_selected(self):
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
		ss=StorageSync()
		ss.set_dbpath(self.dbpath)
		for record in self.iter_selected():
			ss.queue_record(record)
		self.model().select()
	
	def exclude(self):
		"""Move selection to sync_exclude table"""
		ss=StorageSync()
		ss.set_dbpath(self.dbpath)
		for record in self.iter_selected():
			ss.exclude_record(record)
		self.model().select()
		

class SyncWidget(QtGui.QWidget):
	"""Allows the user to control sync behavior."""
	ch=QtCore.pyqtSignal()
	dbpath=False
	def __init__(self,parent=None):
		super(SyncWidget,self).__init__(parent)
		self.transfer=TransferThread(self)
		self.storage_sync=StorageSync(self.transfer)
		dbpath=confdb['database']
		#Create if missing
		try:
			db=indexer.Indexer(dbpath)
		except:
			return
		self.dbpath=dbpath
		self.storage_sync.set_dbpath(dbpath)
		self.lay=QtGui.QVBoxLayout()
		
		self.tab_approve=SyncTable(self.dbpath,'sync_approve',parent=self)
		self.lay.addWidget(self.tab_approve)
		
		self.tab_queue=SyncTable(self.dbpath,'sync_queue',parent=self)
		self.lay.addWidget(self.tab_queue)
		
# 		self.tab_exclude=SyncTable(self.dbpath,'sync_exclude',parent=self)
# 		self.lay.addWidget(self.tab_exclude)
		
		self.setLayout(self.lay)
		
	def set_server(self,server):
		self.storage_sync.prepare(self.dbpath,server)
		
	def loop(self):
		"""Do one collect/download loop"""
		if not self.dbpath:
			return False
		if not self.storage_sync.server:
			return False
		n= self.storage_sync.loop()
		if n:
			self.ch.emit()
		if not len(self):
			self.hide()
		if self.storage_sync.tab_len('sync_queue'):
			self.tab_queue.show()
		else:
			self.tab_queue.hide()
	
	def __len__(self):
		return len(self.storage_sync)
		

