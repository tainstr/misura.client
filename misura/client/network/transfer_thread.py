#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Download/upload thread"""
import os
import urllib2
import urllib
from time import sleep

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtCore
from ...canon import indexer, csutil
from mproxy import urlauth, dataurl


class TransferThread(QtCore.QThread):
    dlStarted = QtCore.pyqtSignal(str, str)
    """Emitted when a new download is started. (url, local path)"""
    dlFinished = QtCore.pyqtSignal(str, str)
    """Finished download - url, local path. (url, local path)"""
    dlAborted = QtCore.pyqtSignal(str, str)
    """Aborted download - url, local path. (url, local path)"""
    dlSize = QtCore.pyqtSignal(int)
    """New total download dimension for current file (bytes)"""
    dlDone = QtCore.pyqtSignal(int)
    """Already downloaded bytes"""
    dlWaiting = QtCore.pyqtSignal(str, str, int)
    """Waiting to reserve the file uid for download. (url, local path,progress)"""
    aborted = False
    retry = 30
    chunk = 1024**2
    size = 0
    done = 0

    def __init__(self, url=False, outfile=False, uid=False, server=False, dbpath=False, post=False, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.url = url
        """directly download URL to outfile"""

        self.outfile = outfile
        """local file where to save the downloaded data, or local source for upload data"""

        self.dbpath = dbpath
        """location of local database where to append downloaded test files"""

        self.uid = uid
        """remote test UID to be searched and downloaded"""

        self.server = server
        """remote server object"""

        self.post = post
        """POST dictionary used for uploading files"""

        self.prefix = 'Download: '
        """Prefix for transfer job in pending tasks"""
        
        

    @property
    def pid(self):
        """Task identification name"""
        r = self.prefix
        if self.url:
            url = self.url.split('@')[-1]
            r += url
        if self.outfile:
            r += '\nto ' + self.outfile
        return r

    @property
    def wpid(self):
        """Waiting task id"""
        url = self.url.split('@')[-1]
        return 'Waiting: {} \nto {}'.format(url, self.outfile)

    def task_new(self, size):
        """Start new download task"""
        self.tasks.jobs(size, self.pid)
        # End waiting task, if started
        self.tasks.done(self.wpid)

    def task_up(self, done):
        """Update current download task"""
        self.tasks.job(done, self.pid)

    def task_end(self, *foo):
        """End current download task"""
        self.tasks.done(self.pid)
        self.tasks.done(self.wpid)

    def task_wait(self, url, outfile, progress):
        """Manage an UID reservation task"""
        if progress == 0:
            # Start a new waiting task
            self.tasks.jobs(self.retry, self.wpid)
        else:
            self.tasks.job(progress, self.wpid)

    def abort(self, pid=False):
        """Set the current download as aborted"""
        if (not pid) or (pid == self.pid):
            self.aborted = True
        return self.aborted

    def set_tasks(self, tasks=None):
        """Install a graphical pending task manager for this thread"""
        self.tasks = tasks
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
        self.connect(self.tasks, QtCore.SIGNAL(
            'sig_done(QString)'), self.abort, QtCore.Qt.QueuedConnection)
        return True

    def prepare_opener(self, url):
        """Install the basic authentication url opener"""
        user, passwd, url = urlauth(url)
        # Connection to data
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(
            realm='MISURA', uri=url, user=user, passwd=passwd)
        opener = urllib2.build_opener(auth_handler)
        # ...and install it globally so it can be used with urlopen.
        urllib2.install_opener(opener)
        return url

    def download_url(self, url, outfile):
        """Download from url and save to outfile path"""
        logging.debug('download url', url, outfile)
        self.aborted = False
        self.prefix = 'Download: '
        self.url = url
        outfile = csutil.incremental_filename(outfile)
        self.outfile = outfile
        url = self.prepare_opener(url)
        self.dlStarted.emit(url, outfile)
        logging.debug('TransferThread.download_url', url)
        req = urllib2.urlopen(url)
        self.size = int(req.info().getheaders('Content-Length')[0])
        self.dlSize.emit(self.size)
        # Determine a unique filename
        
        if os.path.exists(outfile):
            
            logging.info('Renaming output file to unique name')
            
        # FIXME: maximum recursion depth on big files or chunks too little
        self.done = 0
        with open(outfile, 'wb') as fp:
            while not self.aborted:
                #                 sleep(0.1) # Throttle
                chunk = req.read(self.chunk)
                if not chunk:
                    break
                fp.write(chunk)
                self.done += len(chunk)
                self.dlDone.emit(self.done)
        # Remove if aborted
        if self.aborted:
            logging.debug(
                'Download ABORTED. Removing local file:', outfile)
            os.remove(outfile)
            self.dlAborted.emit(url, outfile)
        # Append to db if defined
        elif self.dbpath and os.path.exists(self.dbpath):
            db = indexer.Indexer(self.dbpath)
            db.appendFile(outfile)
            db.close()
        self.dlFinished.emit(url, outfile)
        return True

    def download_uid(self, server, uid, outfile=False, retry=20):
        """Download test `uid` from `server` storage."""
        url, loc = dataurl(server, uid)
        self.url = url
        # Autocalc outfile from dbpath
        if not outfile and self.dbpath:
            loc = loc.split('/')
            outfile = os.path.dirname(self.dbpath)
            outfile = os.path.join(outfile, *loc)
            # Create nested directory structure
            d = os.path.dirname(outfile)
            if not os.path.exists(d):
                os.makedirs(d)
        if not outfile:
            raise BaseException('Output file was not specified')
        self.outfile = outfile
        # Try to reserve the file for download
        itr = 0
        self.retry = retry
        # Remove other reservations and close file
        while not server.storage.test.free(uid) and not self.aborted:
            self.dlWaiting.emit(url, outfile, itr)
            if itr >= self.retry:
                break
            logging.debug('Waiting for uid reservation', uid)
            sleep(1)
            itr += 1
            if self.aborted:
                logging.debug('Aborted waiting for uid reservation', uid)
                self.dlAborted.emit(url, outfile)
                return False
        # Reserve again
        server.storage.test.reserve(uid)
        # Abort if not reserved
        if not server.storage.test.is_reserved(uid):
            logging.debug('Cannot reserve UID for download', uid, url)
            self.dlAborted.emit(url, outfile)
            return False
        self.download_url(url, outfile)
        # Free uid for remote opening and next download
        server.storage.test.free(uid)
        return outfile
    
    @property
    def isRunning(self):
        if self.aborted:
            return False
        if self.size==self.done:
            return False
        return True

    def upload(self, url, localfile, post):
        """
        `url` like .../RPC/full/obj/path
        `post` {'opt':,'filename':False}
        """
        self.prefix = 'Upload: '
        opt = post['opt']
        remotefile = post.get('filename', False)
        if not remotefile:
            remotefile = os.path.basename(localfile)
        url = self.prepare_opener(url)
        self.dlStarted.emit(url, localfile)
        fp = open(localfile, 'rb')
        fp.seek(0, 2)
        self.size = fp.tell()
        fp.seek(0)
        self.done = 0
        self.dlSize.emit(self.size)
        while fp:
            if self.aborted:
                data = ''
            else:
                data = fp.read(self.chunk)
            enc = urllib.urlencode({'opt': opt,
                                    'filename': remotefile,
                                    'data': data})
            logging.debug('urlopen', url, opt, remotefile)
            content = urllib2.urlopen(url=url, data=enc).read()
            logging.debug('Transferred chunk', content)
            self.done += len(data)
            if len(data) == 0:
                fp.close()
                fp = False
            self.dlDone.emit(self.done)
#             sleep(0.1)
        # Remove if aborted
        if self.aborted:
            logging.debug('Upload ABORTED at', self.done)
            self.dlAborted.emit(url, localfile)
        self.dlFinished.emit(url, localfile)

    def run(self):
        """Download the configured file in a separate thread"""
        # Send file to remote url
        if self.post:
            if not (self.url and self.outfile):
                logging.debug('TransferThread upload impossible: url, outfile, post: %s %s %s',
                              self.url, self.outfile, self.post)
                return
            self.upload(self.url, self.outfile, self.post)
        # Download specific UID from server storage
        elif self.uid:
            if not self.server and (not self.outfile or not self.dbpath):
                logging.debug('TransferThread uid download impossible: server, uid, outfile: %s %s %s',
                              self.server, self.uid, self.outfile)
                return
            # Reconnect because we are in a different thread
            self.server.connect()
            self.download_uid(self.server, self.uid, self.outfile)
        # Download specific complete URL to outfile
        elif self.url:
            if not self.outfile:
                logging.debug('TransferThread url download impossible: outfile: %s',
                              self.outfile)
                return
            self.download_url(self.url, self.outfile)
        return
