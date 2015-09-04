# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
import os
from PyQt4 import QtCore, QtGui

from m3db import fimg

class ImagePreviewModel(QtCore.QAbstractTableModel):

    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.dat = []
        self.path = ''

    def setPathData(self, path, data):
        self.dat = []
        self.path = ''
        if not os.path.exists(os.path.dirname(path)):
            logging.debug('%s %s', 'Path does not exists', path)
            QtCore.QAbstractTableModel.reset(self)
            return
        self.dat = data
        self.path = path
        QtCore.QAbstractTableModel.reset(self)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.dat)

    def rowCount(self, index=QtCore.QModelIndex()):
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        if role == QtCore.Qt.DisplayRole:
            code = os.path.basename(self.path)
            num = self.dat[index.column()][fimg.Numero_Immagine]
            img = '%s.%03i' % (self.path, int(num))
            return img

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                h = u'%.1f°C' % self.dat[section][fimg.Temp]
                return h
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

maxImageCacheSize = 500


class ImageDecoder(QtCore.QThread):

    def __init__(self, parent=None, maxWidth=100):
        QtCore.QThread.__init__(self, parent)
        self.names = [False] * maxImageCacheSize
        self.images = {}
        self.queue = []
        self.maxWidth = maxWidth

    def cache(self, path):
        if path in self.names:
            return self.images[path]
        pix = QtGui.QImage()
        img = open(path, 'rb').read()
        img = bitmap.decompress(img)
        pix.loadFromData(img, 'BMP')
        pix = pix.scaledToWidth(self.maxWidth)
        self.names.append(path)
        self.images[path] = pix
        # keep image cache length
        d = self.names.pop(0)
        if d:
            del self.images[d]
        return pix

    def append(self, path, index):
        self.queue.append([path, index])

    def get(self, path):
        if not path in self.names:
            return False
        return self.images[path]

    def run(self):
        while True:
            if len(self.queue) == 0:
                sleep(.1)
                continue
            # Always read last requested data
            path, index = self.queue.pop(-1)
            self.cache(path)
            model = index.model()
            self.emit(QtCore.SIGNAL('cached(QModelIndex)'), index)


class ImagePreviewDelegate(QtGui.QItemDelegate):

    """Delegato per la visualiazzazione delle celle nella tabella immagini"""

    def __init__(self, parent=None):
        QtGui.QItemDelegate.__init__(self, parent)
        self.maxWidth = 100
        self.decoder = ImageDecoder(self)
        self.connect(
            self.decoder, QtCore.SIGNAL('cached(QModelIndex)'), parent.update)
        self.decoder.start()

    def paint(self, painter, option, index):
        """Ricezione e disegno delle immagini"""
        model = index.model()
        path = model.data(index)
        img = self.decoder.get(path)

        if img:
            pix = QtGui.QPixmap.fromImage(img)
            painter.save()
            painter.translate(option.rect.x(), option.rect.y())
            painter.drawPixmap(0, 0, pix.width(), pix.height(), pix)
            painter.restore()
            self.parent().resizeRowToContents(index.row())
        else:
            self.decoder.append(path, index)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.maxWidth, self.maxWidth)

    def zoom(self, width=100):
        self.maxWidth = width
        self.parent().resizeRowsToContents()
        self.parent().resizeColumnsToContents()

    def zoomIn(self):
        self.zoom(self.maxWidth * 1.1)

    def zoomOut(self):
        self.zoom(self.maxWidth * 0.9)


class ImagePreview(QtGui.QTableView):

    """Table for previewing images contained in the test."""

    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.dmodel = ImagePreviewModel(self)
        self.setModel(self.dmodel)
        self.setItemDelegate(ImagePreviewDelegate(self))
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.menu = QtGui.QMenu(self)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.zoomIn = self.menu.addAction(
            'Zoom In', self.itemDelegate().zoomIn)
        self.zoomOut = self.menu.addAction(
            'Zoom Out', self.itemDelegate().zoomOut)
        self.zoomOk = self.menu.addAction(
            'Zoom Reset', self.itemDelegate().zoom)
        self.setMinimumSize(0, 150)

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))