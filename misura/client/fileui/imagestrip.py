#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from row import RowView
from PyQt4 import QtGui, QtCore
from minimage import MiniImage


class ImageStrip(QtGui.QWidget):

    """Image strip"""
    t = 0
    idx = 0
    step = 10
    bytime = False
    autofollow = False
    decoder = False

    def __init__(self, n=5, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.lay = QtGui.QGridLayout()
        self.setLayout(self.lay)
        self.n = n
        self.labels = []
        self.menu = QtGui.QMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.menu.addAction('Change length', self.chLen)
        self.menu.addAction('Change rows', self.chRows)
        self.actIndex = self.menu.addAction('Step by index', self.by_index)
        self.actIndex.setCheckable(True)
        self.actTime = self.menu.addAction('Step by time', self.by_time)
        self.actTime.setCheckable(True)

    def set_doc(self, doc, datapath=False):
        logging.debug('%s %s %s', 'ImageStrip.set_doc', doc, datapath)
        self.doc = doc
        self.idx = 0
        self.t = 0
        self.rows = 1
        self.decoder = doc.decoders.get(datapath, False)
        self.set_idx(0)
        self.setLen(self.n)

        if self.decoder:
            self.connect(self.decoder, QtCore.SIGNAL('reset()'), self.setLen)

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))
        self.actTime.setChecked(self.bytime)
        self.actIndex.setChecked(not self.bytime)

    def chLen(self):
        n = QtGui.QInputDialog.getInt(
            self, "New length", "Change number of images:", self.n, 1, 50)
        if n[1]:
            self.setLen(n[0])

    def chRows(self):
        n = QtGui.QInputDialog.getInt(
            self, "Set rows", "Change number of rows displayed:", self.rows, 1, 10)
        if n[1]:
            self.rows = n[0]
            self.setLen(self.n)

    def by_index(self):
        val, st = QtGui.QInputDialog.getInt(
            self, "Step by index", "Display one image every N:", value=self.step, min=1, step=1)
        if not st:
            return
        self.step = val
        self.bytime = False
        self.set_idx()

    def by_time(self):
        # TODO: by_time stepping
        val, st = QtGui.QInputDialog.getInt(
            self, "Step by time", "Display one image every N seconds:", value=self.step, min=1, step=1)
        if not st:
            return
        self.step = val
        self.bytime = True
        self.set_idx()

    def route_meta_changed(self, keys):
        logging.debug('%s %s', 'routing meta keys', keys)
        for lbl in self.labels:
            lbl.sync_meta_keys(keys)

    def setLen(self, n=-1):
        """Changes the number of visible images"""
        if n < 0:
            n = self.n
        self.n = n
        for lbl in self.labels:
            lbl.close()
            del lbl
        self.labels = []
        if self.decoder:
            datapath = self.decoder.datapath
        else:
            datapath = False
        for i in range(n):
            row = i % self.rows
            col = i / self.rows
            lbl = MiniImage(self.doc, datapath, parent=self)
            self.lay.addWidget(lbl, row, col)
            self.labels.append(lbl)
            lbl.metaChanged.connect(self.route_meta_changed)
        # The last label holds the current idx, and emits current time signal
        self.connect(
            self.labels[-1], QtCore.SIGNAL('set_time(float)'), self.emitSetTime)
        self.set_idx()

        return True

    def emitSetTime(self, t):
        """Route setTime signals received by the last MiniImage"""
        self.t = t
        logging.debug('%s %s', 'ImageStrip.emitSetTime', t)
        self.emit(QtCore.SIGNAL('set_time(float)'), t)

    def set_time(self, t):
        """Find the nearest index to time `t` and set myself on that idx"""
        logging.debug('%s %s', 'ImageStrip.setTime', t)
        idx = self.decoder.get_time(self.decoder.datapath)
        logging.debug('%s %s', 'ImageStrip.setTime: idx', idx)
        return self.set_idx(idx)

    def set_idx(self, idx=-1):
        """Sets the current end index."""
        if len(self.labels) < self.n:
            return
        if self.n == 0:
            return
        logging.debug('%s %s', 'strip idx', idx)
        if idx < 0:
            idx = self.idx

        for label_index in range(self.n):
            index_with_step =  max(0, idx + (label_index * self.step) - 1)
            self.labels[label_index].set_idx(index_with_step)

        self.idx = idx
        self.emit(QtCore.SIGNAL('set_idx(int)'), idx)


class Slider(QtGui.QWidget):
    autofollow = False

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.slider = QtGui.QScrollBar(parent=self)
        self.slider.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.slider.setTracking(False)
        self.slider.setOrientation(QtCore.Qt.Horizontal)

        self.cbPath = QtGui.QComboBox(self)

        self.lay = QtGui.QHBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.lay.addWidget(self.slider)
        self.lay.addWidget(self.cbPath)
        self.setLayout(self.lay)
        self.connect(
            self.cbPath, QtCore.SIGNAL('currentIndexChanged(int)'), self.choice)
        self.connect(self.slider, QtCore.SIGNAL('sliderReleased()'), self.slider_released)

    def value(self):
        return self.slider.value()

    def slider_released(self):
        self.emit(QtCore.SIGNAL('sliderReleased()'))

    def set_doc(self, doc):
        self.doc = doc
        self.reset(True)
        self.connect(self.doc, QtCore.SIGNAL('updated()'), self.setLen)

    def setLen(self):
        follow = self.autofollow
        if follow:
            follow = self.slider.value() == self.slider.maximum()
        L = 0
        if self.decoder:
            L = len(self.decoder)
        self.slider.setMaximum(L)
        logging.debug('%s %s', 'Slider.setLen', L)
        if follow:
            logging.debug('%s', 'Slider.setLen autofollow')
            self.set_idx(L)

    def choice(self, foo=0):
        self.reset(choice=True)

    def reset(self, choice=False):
        fp = self.doc.proxy
        if not fp:
            return
        self.disconnect(
            self.cbPath, QtCore.SIGNAL('currentIndexChanged(int)'), self.choice)

        # Get dat group
        i = self.cbPath.currentIndex()
        cgr = str(self.cbPath.itemData(i))
        logging.debug('%s %s %s', 'current group', i, cgr)

        # Update group combo
        self.cbPath.clear()
        gr = []
        for g in self.doc.decoders.keys():
            self.cbPath.addItem(g, g)
            gr.append(g)
        if i < 0 and len(gr) > 0:
            cgr = gr[0]
            i = 0
        self.cbPath.setCurrentIndex(i)
        self.connect(
            self.cbPath, QtCore.SIGNAL('currentIndexChanged(int)'), self.choice)

        # Reset decoder
        if choice:
            logging.debug('%s %s', 'resetting to', cgr)
            self.decoder = self.doc.decoders.get(cgr, False)
            n = getattr(self.decoder, 'datapath', False)
            logging.debug('%s %s', 'resetted to', n)
            if n:
                self.emit(QtCore.SIGNAL('datapathChanged(QString)'), n)
        m = 0
        if self.decoder:
            m = len(self.decoder)
        self.slider.setMaximum(m)
        self.slider.setMinimum(0)
        self.slider.setValue(0)
        logging.debug('%s', 'done')

    def set_idx(self, idx):
        if self.slider.maximum() == 0:
            return
        self.slider.setValue(idx)
        self.emit(QtCore.SIGNAL('set_idx(int)'), idx)


class ImageSlider(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.strip = ImageStrip(parent=self)
        self.connect(
            self.strip, QtCore.SIGNAL('set_time(float)'), self.emitSetTime)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.strip.showMenu)

        self.stripArea = QtGui.QScrollArea(self)
        self.stripArea.setWidgetResizable(True)
        self.stripArea.setWidget(self.strip)
        self.stripArea.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self.stripArea, QtCore.SIGNAL(
            'customContextMenuRequested(QPoint)'), self.strip.showMenu)

        # Slider for image navigation
        self.slider = Slider(self)
        self.slider.slider.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self.slider.slider, QtCore.SIGNAL(
            'customContextMenuRequested(QPoint)'), self.strip.showMenu)
#		self.connect(self.slider,QtCore.SIGNAL('set_idx(int)'),self.set_idx)
        self.slider.slider.valueChanged.connect(self.strip.set_idx)
        self.slider.slider.sliderMoved.connect(self.strip.set_idx)
        self.connect(self.slider, QtCore.SIGNAL(
            'datapathChanged(QString)'), self.setPath)
        self.lay = QtGui.QVBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.lay.addWidget(self.slider)
        self.lay.addWidget(self.stripArea)
        self.setLayout(self.lay)

        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.strip.showMenu)
        self.connect(self.slider, QtCore.SIGNAL('sliderReleased()'), self.slider_released)

    def slider_released(self):
        self.emit(QtCore.SIGNAL('sliderReleased()'))

    def emitSetTime(self, t):
        """Route setTime signals received by the ImageStrip"""
        logging.debug('%s %s', 'ImageSlider.setTime', t)
        self.emit(QtCore.SIGNAL('set_time(float)'), t)

    def value(self):
        return self.slider.value()

    @property
    def idx(self):
        return self.value()

    @property
    def t(self):
        return self.strip.t

    def set_doc(self, doc):
        self.doc = doc
        self.slider.set_doc(doc)

    def setPath(self, path):
        self.strip.set_doc(self.doc, str(path))

    def set_idx(self, idx):
        if self.slider.slider.maximum() == 0:
            return
        self.disconnect(
            self.slider, QtCore.SIGNAL('set_idx(int)'), self.set_idx)
        self.disconnect(
            self.strip, QtCore.SIGNAL('set_idx(int)'), self.set_idx)
        self.emit(QtCore.SIGNAL('set_idx(int)'), idx)
        self.slider.set_idx(idx)
        self.strip.set_idx(idx)
        self.connect(self.slider, QtCore.SIGNAL('set_idx(int)'), self.set_idx)
        self.connect(self.strip, QtCore.SIGNAL('set_idx(int)'), self.set_idx)

    def set_time(self, t):
        if self.slider.decoder:
            idx = self.slider.decoder.get_time(t)
        else:
            idx = int(t)

        self.set_idx(idx)