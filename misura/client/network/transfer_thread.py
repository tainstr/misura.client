#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Download/upload thread"""
import os
import urllib2, urllib
import logging

from PyQt4 import QtCore
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


def remote_dbdir(server):
	"""Calc remote database directory path"""
	# Filter away the misura.sqlite filename
	p=server.storage.get_dbpath().split('/')[:-1]
	r= '/'.join(p)
	logging.debug('%s %s', 'remote_dbdir', r)
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
	return url,p

class TransferThread(QtCore.QThread):
	dlStarted=QtCore.pyqtSignal(str,str)
	"""Emitted when a new download is started. (url, local path)"""
	dlFinished=QtCore.pyqtSignal(str,str)
	"""Finished download - url, local path. (url, local path)"""
	dlAborted=QtCore.pyqtSignal(str,str)
	"""Aborted download - url, local path. (url, local path)"""
	dlSize=QtCore.pyqtSignal(int)
	"""New total download dimension for current file (bytes)"""
	dlDone=QtCore.pyqtSignal(int)
	"""Already downloaded bytes"""
	dlWaiting=QtCore.pyqtSignal(str,str,int)
	"""Waiting to reserve the file uid for download. (url, local path,progress)"""
	aborted=False
	retry=30
	def __init__(self,url=False,outfile=False,uid=False,server=False,dbpath=False,post=False,parent=None):
		QtCore.QThread.__init__(self,parent)
		self.url=url
		self.outfile=outfile
		self.dbpath=dbpath
		self.uid=uid
		self.server=server
		self.post=post
		self.prefix='Download: '
		
	@property
	def pid(self):
		"""Task identification name"""
		return self.prefix+('{} \nto {}'.format(self.url,self.outfile))
	
	@property
	def wpid(self):
		"""Waiting task id"""
		return 'Waiting: {} \nto {}'.format(self.url,self.outfile)
		
	def task_new(self,size):
		"""Start new download task"""
		self.tasks.jobs(size,self.pid)
		# End waiting task, if started
		self.tasks.done(self.wpid)
		
	def task_up(self,done):
		"""Update current download task"""
		self.tasks.job(done,self.pid)
		
	def task_end(self,*foo):
		"""End current download task"""
		self.tasks.done(self.pid)
		self.tasks.done(self.wpid)
		
	def task_wait(self,url,outfile,progress):
		"""Manage an UID reservation task"""
		if progress==0:
			# Start a new waiting task
			self.tasks.jobs(self.retry,self.wpid)
		else:
			self.tasks.job(progress,self.wpid)
			
	def abort(self,pid=False):
		"""Set the current download as aborted"""
		if (not pid) or (pid==self.pid):
			self.aborted=True
		return self.aborted
		
	def set_tasks(self,tasks=None):
		"""Install a graphical pending task manager for this thread"""
		self.tasks=tasks
		if tasks is None:
			self.dlSize.disconnect(self.task_new)
			self.dlDone.disconnect(self.task_up)
			self.dlFinished.disconnect(self.task_end)
			self.dlAborted.disconnect(self.task_end)
			self.dlWaiting.disconnect(self.task_wait)
			return False
		self.dlSize.connect(self.task_new)
		self.dlDone.connect(self.task_up)
		self.dlFinished.connect(self.task_end)
		self.dlAborted.connect(self.task_end)
		self.dlWaiting.connect(self.task_wait)
		self.tasks.sig_done.connect(self.abort)
		return True
	
	def prepare_opener(self,url):
		user,passwd,url=urlauth(url)
		# Connection to data
		auth_handler= urllib2.HTTPBasicAuthHandler()
		auth_handler.add_password(realm='MISURA', uri=url, user=user, passwd=passwd)
		opener = urllib2.build_opener(auth_handler)
		# ...and install it globally so it can be used with urlopen.
		urllib2.install_opener(opener)		
		return url
				
	def download_url(self,url,outfile):
		"""Download from url and save to outfile path"""
		logging.debug('%s %s %s', 'download url', url, outfile)
		self.prefix='Download: '
		self.url=url
		self.outfile=outfile
		url=self.prepare_opener(url)
		self.dlStarted.emit(url,outfile)
		req = urllib2.urlopen(url)
		dim=int(req.info().getheaders('Content-Length')[0])
		self.dlSize.emit(dim)
		CHUNK = 16 * 1024
		done=0
		with open(outfile, 'wb') as fp:
			while not self.aborted:
# 				sleep(0.1) # Throttle
				chunk = req.read(CHUNK)
				if not chunk: break
				fp.write(chunk)
				done+=len(chunk)
# 				logging.debug('%s %s %s', 'DONE', done, dim)
				self.dlDone.emit(done)
		# Remove if aborted
		if self.aborted:
			logging.debug('%s %s', 'Download ABORTED. Removing local file:', outfile)
			os.remove(outfile)
			self.dlAborted.emit(url,outfile)
		# Append to db if defined
		elif self.dbpath and os.path.exists(self.dbpath):
			db=indexer.Indexer(self.dbpath)
			db.appendFile(outfile)
			db.close()
		self.dlFinished.emit(url,outfile)
		return True
	
	def download_uid(self,server,uid,outfile,retry=20):
		"""Download test `uid` from `server` storage."""
		url,loc=dataurl(server,uid)
		self.url=url
		# Autocalc outfile from dbpath
		if not outfile and self.dbpath:
			loc=loc.split('/')
			outfile=os.path.dirname(self.dbpath)
			outfile=os.path.join(outfile,*loc)
			# Create nested directory structure
			d=os.path.dirname(outfile)
			if not os.path.exists(d):
				os.makedirs(d)
		if not outfile:
			raise BaseException('Output file was not specified')
		self.outfile=outfile
		# Try to reserve the file for download
		itr=0
		self.retry=retry
		# Remove other reservations and close file
		while not server.storage.test.free(uid) and not self.aborted:
			self.dlWaiting.emit(url,outfile,itr)
# 			sleep(1)
			if itr>=self.retry:
				break
			logging.debug('%s %s', 'Waiting for uid reservation', uid)
			itr+=1
		if self.aborted:
			logging.debug('%s %s', 'Aborted waiting for uid reservation', uid)
			self.dlAborted.emit(url,outfile)
			return False
		# Reserve again
		server.storage.test.reserve(uid)
		# Abort if not reserved
		if not server.storage.test.is_reserved(uid):
			logging.debug('%s %s %s', 'Cannot reserve UID for download', uid, url)
			self.dlAborted.emit(url,outfile)
			return False
		self.download_url(url,outfile)
		# Free uid for remote opening and next download
		server.storage.test.free(uid)
		return True
	
	def upload(self,url,localfile,post):
		"""
		`url` like .../RPC/full/obj/path
		`post` {'opt':,'filename':False}
		"""
		self.prefix='Upload: '
		opt=post['opt']
		remotefile=post.get('filename',False)
		if not remotefile:
			remotefile=os.path.basename(localfile)
		url=self.prepare_opener(url)
		self.dlStarted.emit(url,localfile)
		CHUNK = 1024 * 1024
		fp=open(localfile, 'rb')
		fp.seek(0,2)
		dim=fp.tell()
		fp.seek(0)
		done=0
		self.dlSize.emit(dim)
		while fp:
			if self.aborted:
				data=''
			else:
				data=fp.read(CHUNK)
			enc=urllib.urlencode({'opt' : opt,
	                         'filename'  : remotefile,
	                         'data':data})
			logging.debug('%s %s %s %s', 'urlopen', url, opt, remotefile)
			content = urllib2.urlopen(url=url, data=enc).read()
			logging.debug('%s %s', 'Transferred chunk', content)
			done+=len(data)
			if len(data)==0:
				fp.close()
				fp=False
			self.dlDone.emit(done)
# 			sleep(0.1)
		# Remove if aborted
		if self.aborted:
			logging.debug('%s %s', 'Upload ABORTED at', done)
			self.dlAborted.emit(url,localfile)
		self.dlFinished.emit(url,localfile)		
		
	def run(self):
		"""Download the configured file in a separate thread"""
		if (not (self.outfile or self.dbpath)) or not ((self.uid and self.server) or self.url) or not (self.post and self.outfile and self.url):
			logging.debug('%s %s %s %s %s %s', 'Impossible to download', self.url, self.uid, self.server, self.outfile, self.post)
		if self.post:
			self.upload(self.url,self.outfile,self.post)
		elif self.uid:
			# Reconnect because we are in a different thread
			self.server.connect()
			self.download_uid(self.server,self.uid,self.outfile)
		elif self.url:
			self.download_url(self.url,self.outfile)
			