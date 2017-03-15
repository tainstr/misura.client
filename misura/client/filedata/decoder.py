#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Interfaces for local and remote file access"""

from misura.canon.logger import get_module_logging
from math import sqrt
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore
from time import sleep, time
import tempfile
import traceback
import shutil
import os

from .. import parameters as params
from misura.canon import bitmap
from misura.canon import reference
import proxy


MAX = 10**5
MIN = -10**5


def draw_profile(x, y, margin=(20, 50, 5, 5), contour_only=False, pen_width=0):
    """Draw an x,y profile onto a QImage.
    margin: upper, bottom, left, right"""

    
    if contour_only and pen_width<=0:
        h = max(y)-min(y)
        w = max(x)-min(y)
        pen_width = int((0.01) * sqrt(h**2 + w**2))
        pen_width = max(pen_width, 10)
    else:
        pen_width = 3
        
    m_up, m_btm, m_left, m_right = margin
    x = x - min(x) + m_left + pen_width
    y = y - min(y) + m_up + pen_width
    w = max(x) + m_right + pen_width
    h = max(y) + m_btm + pen_width
    
    lst = list(QtCore.QPointF(ix, y[i]) for i, ix in enumerate(x))
    # Close the polygon
    lst.append(QtCore.QPointF(x[-1], h))
    lst.append(QtCore.QPointF(x[0], h))
    lst.append(QtCore.QPointF(x[0], y[0]))

    # Create a painter path
    qpath = QtGui.QPainterPath()
    qpath.addPolygon(QtGui.QPolygonF(lst))
    qpath.setFillRule(QtCore.Qt.WindingFill)

    pix = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
    # Clear memory (Qt bug)
    pix.fill(QtCore.Qt.transparent)
    #QtGui.QImage.Format_ARGB32_Premultiplied
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    
    # Only contour
    pen = QtGui.QPen(QtCore.Qt.black)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setWidth(pen_width)
    
    if contour_only:
        p.setBrush(QtGui.QBrush(QtCore.Qt.transparent))
    else:
        p.setBrush(QtGui.QBrush(QtCore.Qt.black))
    
    p.setPen(pen)
    # Fill background
    r = pix.rect()
    p.fillRect(r, QtCore.Qt.transparent)
    # Add profile
    p.drawPath(qpath)
    p.end()
    return pix


visibleOptions = ['seqnum', 't', 'T', 'd', 'Sint']


class DataDecoder(QtCore.QThread):

    """Cached image reader and decoder from Misura 4 files. To be run in a separate thread."""
    proxy = False
    datapath = False
    tmpdir = False
    ext = False
    zerotime = -1
    comp = 'JPG'
    comps = set(('JPG', 'PNG'))
    prefix = '0:'
    _len = 0
    contour_only = False
    contour_width = 0

    def __init__(self, parent=None, maxWidth=100):
        QtCore.QThread.__init__(self, parent)
        self.reset()
        self.opt_images = True
        self.opt_profiles = False
        self.connect(self, QtCore.SIGNAL('destroyed(QObject)'), self.close)
        self.connect(
            QtGui.qApp, QtCore.SIGNAL('lastWindowClosed()'), self.close)

    def close(self, *foo):
        logging.debug('CLOSING DataDecoder', self.tmpdir)
        if self.tmpdir and os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)
        self.ok = False
        sleep(.05)
        self.terminate()
        if self.proxy:
            self.proxy.close()

    def setDataPath(self, datapath):
        if self.isRunning():
            self.exit()
            self.wait()
        self.names = [-1] * params.maxImageCacheSize
        self.data = {}
        self.queue = []
        if datapath:
            self.datapath = datapath

        # Clear old tmpdir
        if self.tmpdir:
            shutil.rmtree(self.tmpdir)
        # Create tmpdir
        self.tmpdir = tempfile.mkdtemp()

        # Read metadata about the path
        if (self.proxy is not False) and (self.datapath is not False):
            self.refClassName = self.proxy.get_node_attr(
                self.datapath, '_reference_class')
#            self.ext = self.proxy.get_node_attr(self.datapath, 'type')
            self.ext = self.refClassName
            logging.debug(
                'DataDecoder.setDataPath', datapath, self.refClassName, self.ext)
            self.refclass = getattr(reference, self.refClassName)

        self.emit(QtCore.SIGNAL('reset()'))
        self.ok = True

    def reset(self, proxy=False, datapath=False, prefix='0:'):
        self._len = 0
        self.zerotime = -1
        self.cached_profiles = {}
        self.prefix = prefix
        self.ok = False
        if self.isRunning():
            self.exit()
            self.wait()
        if (not proxy) and self.proxy:
            proxy = self.proxy
        if proxy:
            # 			self.proxy=proxy.copy()
            self.proxy = proxy
        self.setDataPath(datapath)

    def get_len(self, fp=False):
        """Cross thread __len__ retrieval"""
        if not fp:
            fp = self.proxy
        if fp is False or self.datapath is False:
            logging.debug('DataDecoder: no proxy or datapath')
            self._len = 0
            return self._len
        try:
            r = fp.len(self.datapath)
            assert r is not None
        except:
            logging.debug('get_len first pass')
            traceback.print_exc()
            fp = fp.copy()
            try:
                r = fp.len(self.datapath)
            except:
                logging.debug('get_len second pass')
                traceback.print_exc()
                r = 0

        logging.debug('DataDecoder.get_len', r)
        if r is not None:
            self._len = r
        return self._len

    def __len__(self):
        if self.isRunning():
            logging.debug('decoder running', self._len)
            return self._len
        r = 0
        try:
            r = self.get_len()
        except:
            logging.debug('Getting __len__', self.datapath)
            traceback.print_exc()
        return r

    def get_time(self, t):
        if self.ext == 'Profile':
            f = self.proxy.get_time_profile
        else:
            f = self.proxy.get_time_image
        # Compatibility with absolute-time datasets
        if t > self.zerotime:
            t += self.zerotime
        return f(self.datapath, t)

    def get_data(self, seq, fp=False):
        if not fp:
            fp = self.proxy
        if fp is False:
            logging.debug('get_data: no file proxy')
            return False

        sequence_id = '%i' % (seq)

        if self.cached_profiles.has_key(sequence_id):
            entry = self.cached_profiles[sequence_id]
        else:
            t0 = time()
            entry = fp.col_at(self.datapath, seq, True)
            t1 = time()
            logging.debug('DataDecoder entry search', t1 - t0)
            if entry is None or len(entry) <= 5:
                logging.debug('NO DATA', self.datapath, seq, self.ext, entry)
                return False
            self.cached_profiles[sequence_id] = entry

        # Data decoding
        try:
            t, dat = self.refclass.decode(entry)
        except:
            logging.debug('DataDecoder getting', self.datapath, seq)
            traceback.print_exc()
            return False
        # Direct image conversion
        if self.ext == 'Image':
            logging.debug('toQImage', seq)
            # Create a QImage for signalling
            pix = QtGui.QImage()
            L = pix.loadFromData(dat, self.comp)
            if not L:
                self.comp = (self.comps - set([self.comp])).pop()
                pix.loadFromData(dat, self.comp)
# 			pix.loadFromData(QtCore.QByteArray(dat),'JPG')
            return t, pix
        # FIXME: how to detect misura compression? Different Ext? Or different
        # ReferenceClass?
        elif self.ext == 'ImageM3':
            logging.debug('decompressing', seq)
            dat = bitmap.decompress(dat)
            qimg = QtGui.QImage()
            qimg.loadFromData(dat, 'BMP')
            return t, qimg
        # Writing a profile onto an image
        elif self.ext == 'Profile':
            logging.debug('Profile', seq)
            ((w, h), x, y) = dat
            return t, draw_profile(x, y, contour_only=self.contour_only, pen_width=self.contour_width)

        logging.debug('Format not recognized', self.ext)
        return False

    def dequeue(self, seq):
        """Remove from queue an entry which is no longer needed"""
        if seq in self.queue:
            self.queue.remove(seq)

    def cache(self, seq, fp=False):
        """Read image and save in cache"""
        if not fp:
            fp = self.proxy
        if not fp:
            return True
        if seq in self.names:
            return True
        t, dat = self.get_data(seq, fp)
        if not dat:
            return False
        self.names.append(seq)
        self.data[seq] = t, dat
        # keep image cache length
        d = self.names.pop(0)
        if d >= 0:
            del self.data[d]
        return True

    def get(self, seq):
        if self.proxy is False or self.datapath is False:
            logging.debug('proxy', self.proxy)
            logging.debug('datapath', self.datapath)
            return False
        if not (seq in self.names):
            logging.debug('queue', seq)
            self.queue.append(seq)
            # If queue is longer than maximum cache length, remove oldest point
            if len(self.queue) >= params.maxImageCacheSize:
                self.queue.pop(0)
            if not self.isRunning():
                logging.debug('Restart decoder')
                self.start()
            return False
        if self.zerotime < 0:
            self.zerotime = self.proxy.get_node_attr('/conf', 'zerotime')
        t, dat = self.data[seq]
        if self.ext == 'img':
            self.emit(QtCore.SIGNAL('readyImage(QImage)'), dat)
        self.emit(QtCore.SIGNAL('readyFrame()'))
        logging.debug('found data', self.zerotime, t)
        # Compatibility with absolute-time datasets
        if t > self.zerotime:
            t -= self.zerotime
        return t, dat

    def run(self):
        """Runs the decoding in a separate thread"""
        if self.proxy is False:
            logging.debug('No proxy defined')
            return
        fp = self.proxy.copy()
        fp.connect()

        self._len = self.get_len(fp)

        while self.ok:
            if len(self.queue) == 0:
                # Refresh total length
                if isinstance(fp, proxy.RemoteFileProxy):
                    self._len = self.get_len(fp)
                sleep(.2)
                continue
            # Always read last requested data
            seq = self.queue.pop(-1)
            self.cache(seq, fp)
            self.emit(QtCore.SIGNAL('cached(int)'), seq)
            if len(self.queue) == 0:
                self.emit(QtCore.SIGNAL('cached()'))
        fp.close()

    def toggle_run(self):
        pass

    @property
    def stream(self):
        """Is the decoder streaming?"""
        if self.ok and self.isRunning():
            return True
        return False
