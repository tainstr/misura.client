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

def urlauth(url):
	"""Decode and strip away the auth part of an url.
	Returns user, password and clean url"""
	i=url.find('://')+3
	e=url.find('@',i)+1
	auth=url[i:e][:-1]
	user,passwd=auth.split(':')
	url=url[:i]+url[e:]
	return user,passwd,url

class DownloadThread(QtCore.QThread):
	dlStarted=QtCore.pyqtSignal(str,str)
	"""Emitted when a new download is started. url, local path."""
	dlFinished=QtCore.pyqtSignal(str,str)
	"""Finished download - url, local path"""
	dlSize=QtCore.pyqtSignal(int)
	"""New total download dimension for current file (bytes)"""
	dlDone=QtCore.pyqtSignal(int)
	"""Already downloaded bytes"""
	aborted=False
	def __init__(self,url=False,outfile=False,dbpath=False,parent=None):
		QtCore.QThread.__init__(self,parent)
		self.url=url
		self.outfile=outfile
		self.dbpath=False
		
	@property
	def pid(self):
		"""Task identification name"""
		return 'Download: {} to {}'.format(self.url,self.outfile)
		
	def task_new(self,size):
		self.tasks.jobs(size,self.pid)
		
	def task_up(self,done):
		self.tasks.job(done,self.pid)
		
	def task_end(self,*foo):
		self.tasks.done(self.pid)
		
	def set_tasks(self,tasks=None):
		self.tasks=tasks
		if tasks is None:
			self.dlSize.disconnect(self.task_new)
			self.dlDone.disconnect(self.task_up)
			self.dlFinished.disconnect(self.task_end)
			return False
		self.dlSize.connect(self.task_new)
		self.dlDone.connect(self.task_up)
		self.dlFinished.connect(self.task_end)
		self.tasks.sig_done.connect(self.abort)
		return True
				
	def abort(self,pid=False):
		if (not pid) or (pid==self.pid):
			self.aborted=True
		return self.aborted
	
	def download_url(self,url,outfile):
		"""Download from url and save to outfile path"""
		print 'download url',url,outfile
		user,passwd,url=urlauth(url)
		self.dlStarted.emit(url,outfile)
		# Connection to data
		auth_handler= urllib2.HTTPBasicAuthHandler()
		auth_handler.add_password(realm='MISURA', uri=url, user=user, passwd=passwd)
		opener = urllib2.build_opener(auth_handler)
		# ...and install it globally so it can be used with urlopen.
		urllib2.install_opener(opener)
		req = urllib2.urlopen(url)
		dim=int(req.info().getheaders('Content-Length')[0])
		self.dlSize.emit(dim)
		CHUNK = 16 * 1024
		done=0
		with open(outfile, 'wb') as fp:
			while not self.aborted:
				chunk = req.read(CHUNK)
				if not chunk: break
				fp.write(chunk)
				done+=len(chunk)
				print 'DONE',done,dim
				self.dlDone.emit(done)
		# Remove if aborted
		if self.aborted:
			print 'ABORTED. Removing local file:',outfile
			os.remove(outfile)
		# Append to db if defined
		elif self.dbpath and os.path.exists(self.dbpath):
			db=indexer.Indexer(self.dbpath)
			db.appendFile(outfile)
			db.close()
		self.dlFinished.emit(url,outfile)
		return True
		
	def run(self):
		"""Download the configured file in a separate thread"""
		if False in (self.url,self.outfile):
			print 'Impossible to download',self.url,self.outfile
		self.download_url(self.url,self.outfile)
		
def remote_dbdir(server):
	"""Calc remote database directory path"""
	# Filter away the misura.sqlite filename
	p=server.storage.get_dbpath().split('/')[:-1]
	r= '/'.join(p)
	print 'remote_dbdir',r
	return r

def dataurl(server,uid):
	"""Calc HTTPS/data url for test file `uid` on `server`"""
	t=getattr(server.storage.test,uid)
	if not t: 
		return False
	p=t.get_path()
	# Remove remote db path from file path
	dbdir=remote_dbdir(server)
	if p.startswith(dbdir):
		p=p[len(dbdir):]
	if not p.startswith('/'):
		p='/'+p
	# Prepend remote HTTPS/data path
	url=server.data_addr+p
	return url

class Sync(DownloadThread):
	"""Synchronization thread running in background and checking presence remote test ids in local db"""
	chunk=25
	waiting=QtCore.pyqtSignal(int)
	"""Update total number of files queued for approval"""
	
	def __init__(self,server,parent=None):
		DownloadThread.__init__(self,parent=parent)
		self.enabled=False
		self.server=server
		self.remote_dbdir=remote_dbdir(server)
		"""Remote db directory"""
		self.serial=self.server['serial']
		"""Server serial number"""
		self.approval=[]
		"""List of UIDs waiting to be approved"""
		
		
	def prepare(self,dbpath=False):
		if not dbpath:
			dbpath=confdb['database']
		self.dbpath=dbpath
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
		self.download_url(url,outfile)
		return True
		
		
class SyncThread(Sync):
	def __init__(self,server,parent=None):
		Sync.__init__(self,server,parent)
	
	def loop(self):
		"""Inner synchronization loop"""
		self.collect()
		if not self.server['isRunning']:
			self.download()
		
	def run(self):
		"""Prepare and loop"""
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

