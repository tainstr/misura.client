#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Database synchronization service and widget"""
import os
import urllib2

from time import sleep
from traceback import print_exc

from PyQt4 import QtCore, QtGui

from ..clientconf import confdb
from ...canon import indexer


class Sync(QtCore.QThread):
	"""Synchronization thread running in background and checking presence remote test ids in local db"""
	chunk=25
	dlStarted=QtCore.pyqtSignal(str,str,str)
	"""Emitted when a new download is started. UID, url, local path."""
	dlSize=QtCore.pyqtSignal(int)
	"""New total download dimension for current file (bytes)"""
	dlDone=QtCore.pyqtSignal(int)
	"""Already downloaded bytes"""
	dlFinished=QtCore.pyqtSignal(str,str,str)
	"""Finished download - UID, url, local path"""
	waiting=QtCore.pyqtSignal(int)
	"""Update total number of files queued for approval"""
	
	def __init__(self,server,parent=None):
		QtCore.QThread.__init__(self,parent)
		self.enabled=False
		self.server=server
		p=self.server.storage.get_dbpath().split('/')[:-1]
		self.remote_dbdir='/'.join(p)
		"""Remote db directory"""
		self.serial=self.server['serial']
		"""Server serial number"""
		self.approval=[]
		"""List of UIDs waiting to be approved"""
		
		
	def prepare(self):
		self.dbpath=confdb['database']
		if not os.path.exists(self.dbpath):
			print 'Database path does not exist!',self.dbpath
			return False
		self.dbdir=os.path.dirname(self.dbpath)
		self.db=indexer.Indexer(self.dbpath)
		self.tot=self.server.storage.get_len() #TODO: recheck and put latest on top
		self.start=self.tot-self.chunk
		if self.start<0: self.start=0
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
		if self.has_uid(uid,'sync_queue'):
			print 'Record already queued',record
			return False
		if self.has_uid(uid, 'sync_exclude'):
			print 'Record was excluded. Enabling.', record
			self.rem_uid(uid,'sync_exclude')
		self.add_record(record,'sync_queue')
		return True
	
	def exclude_record(self,record):
		"""Exclude `record` for download."""
		# Check if previously approved (remove!) or already excluded (exit)
		uid=record[2]
		if self.has_uid(uid,'sync_exclude'):
			print 'Record already excluded',record
			return False
		if self.has_uid(uid, 'sync_queue'):
			print 'Record was queued. Enabling.', record
			self.rem_uid(uid,'sync_queue')
		self.add_record(record,'sync_exclude')
		return True
		
	def collect(self):
		"""Scan through a chunk of rows and check if they exist in local archive."""
		end=self.start+self.chunk
		if end>=self.tot: end=self.tot
		lst=self.server.storage.list(self.start,self.start+25)[::-1]
		for t in lst:
			uid=t[2]
			if self.has_uid(uid,'sync_queue'):
				continue
			if self.has_uid(uid,'sync_exclude'):
				continue
			r=self.db.searchUID(t[2],full=True)
			if r and os.path.exists(r[0]):
				continue
			self.approval.append(t)
		self.start=end
		self.waiting.emit(len(self.approval))
		
	def download(self):
		"""Search for the next file to download"""
		record=self.db.execute_fetchone('SELECT 1 from sync_queue')[0]
		r=self.download_record(record[1:])
		if not r: 
			return False
		self.db.execute('DELETE from sync_queue WHERE rowid={}'.format(record[0]))
		return True
		
	def download_record(self,record):
		"""Start the chunked download of a record"""
		print 'download_record',record
		p=record[0].lstrip(self.remote_dbdir).split('/')
		fn=p.pop(-1)
		d=os.path.join(*p)
		outfile=os.path.join(self.dbdir,fn)
		url=self.server.data_addr+d+'/'+fn
		self.dlStarted.emit(record[2],url,outfile)
		req = urllib2.urlopen(url)
		dim=int(req.info().getheaders('Content-Length')[0])
		self.dlSize.emit(dim)
		CHUNK = 16 * 1024
		done=0
		with open(outfile, 'wb') as fp:
			while True:
				chunk = req.read(CHUNK)
				if not chunk: break
				fp.write(chunk)
				done+=len(chunk)
				print 'DONE',done,dim
				self.dlDone(done)
		
		self.dlFinished.emit(record[2],url,outfile)
		return True
		
	def loop(self):
		self.collect()
		if not self.server['isRunning']:
			self.download()
		
	def run(self):
		self.enabled=self.prepare()
		if not self.enabled:
			return False
		self.server=self.server.copy()
		while self.enabled:
			self.loop()
		print 'Sync service was stopped'
		
		
		
	
	
class SyncTable():
	"""Table showing queued sync files, allowing the user to choose which file to sync."""
	pass

class SyncWidget():
	"""Allows the user to control sync behaviour."""
	pass

