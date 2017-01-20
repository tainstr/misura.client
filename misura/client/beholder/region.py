#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for image analysis"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from overlay import Overlay
from hook import HookPoint, HookRect
from PyQt4 import QtGui, QtCore

from grid import Grid

class BoxRegion(Overlay):

    """Region of Interest visualization"""

    def __init__(self, parentItem, sample=False, Z=1):
        Overlay.__init__(self, parentItem, Z)
        self._opt = 'roi'
        self.remObj = sample
        self.moving = False
        self.pen.setStyle(QtCore.Qt.DotLine)
        self.current = {self._opt: [0, 0, 0, 0]}

        # Graphical elements:
        # ROI Box
        self.box = HookRect(parent=self)
        self.box.hookPress = self.blockUpdates
        self.box.hookRelease = self.setCurrent
        self.box.hook = self.move
        self.box.setPen(self.pen)
        self.box.setZValue(self.Z)
        
        self.grid = Grid(self, self.Z)

        # ROI Corners
        self.ptul = HookPoint(
            w=10, h=10, pen=self.pen, Z=self.Z + 1, parent=self)
        self.ptul.setFlag(QtGui.QGraphicsItem.ItemIgnoresTransformations, True)
        self.ptbr = HookPoint(
            w=10, h=10, pen=self.pen, Z=self.Z + 2, parent=self)
        self.ptbr.setFlag(QtGui.QGraphicsItem.ItemIgnoresTransformations, True)
        # Text label
        self.label = QtGui.QGraphicsTextItem(str(self.Z), parent=self)
        self.label.setDefaultTextColor(self.color)
        self.label.setFlag(
            QtGui.QGraphicsItem.ItemIgnoresTransformations, True)
        self.font = self.label.font()

        # Imposto gli hook dei punti in modo che quando vengono mossi
        # provochino il ridimensionamento del rettangolo
        self.ptul.hook = self.reDim
        self.ptul.hookPress = self.blockUpdates
        # al rilascio del mouse, i valori vengono applicati sul server
        self.ptul.hookRelease = self.setCurrent
        self.ptbr.hook = self.reDim
        self.ptbr.hookPress = self.blockUpdates
        self.ptbr.hookRelease = self.setCurrent

    def cleanUp(self, *foo):
        s = self.parentItem().scene()
        lst = self.box, self.ptul, self.ptbr, self.grid
        for item in lst:
            s.removeItem(item)
            del item

    def unscale(self, factor):
        """Nullify the zooming factor on UI elements"""
        self.box.unscale(factor)

    @property
    def opt(self):
        return set([self._opt])

    @opt.setter
    def opt(self, val):
        if len(val) == 0:
            return
        self._opt = list(val)[0]

    def get(self):
        logging.debug('BoxRegion.get', self.remObj, self._opt)
        re = self.remObj.get(self._opt)
        self.current = {self._opt: re}
        return re

    def setCurrent(self):
        """Sets server-side option according to visible rectangle."""
        r = self.box.rect()
        r = [self.box.x() + r.x(), self.box.y() + r.y(), r.width(), r.height()]
        logging.debug('setting rect', r)
        self.remObj[self._opt] = r
        self.syncPoints()
        self.get()
        self.unblockUpdates()

    def syncPoints(self):
        """Resize points on the rectangle"""
        r = self.box.rect()
        f = self.zoom_factor
        d = self.ptul.width() / f
        d2 = d / 2  # pt radius
        self.ptul.setPos(r.x() - d2, r.y() - d2)
        d = self.ptbr.width() / f
        d2 = d / 2  # pt radius
        self.ptbr.setPos(r.x() + r.width() - d2, r.y() + r.height() - d2)
        self.grid.set_length()

    def up(self):
        """Read and redraw server values."""
        if self.moving:
            logging.debug('BoxRegion is moving')
            return
        if not self.isVisible():
            logging.debug('BoxRegion not visible')
            return False
        if not self.validate():
            logging.debug('BoxRegion not validated')
            return False
#		r = self.get()
        r = self.current[self._opt]
        if r is None:
            logging.debug('Region UP error: no values', r)
        x, y, w, h = r
        self.box.setPos(0, 0)
        self.box.setRect(QtCore.QRectF(x, y, w, h))
        self.syncPoints()
        self.label.setPos(QtCore.QPointF(x, y))
#		print 'updated', self, self.current['roi']
        return True

    def reDim(self):
        """Redraw rect so it corresponds to hook points positions."""
        rul = self.ptul.rect()
        rbr = self.ptbr.rect()
        # coords are relative to rect() x,y points:
        d2 = self.ptul.width() / 2 / self.zoom_factor
        x = rul.x() + self.ptul.x() + d2
        y = rul.y() + self.ptul.y() + d2
        w = rbr.x() + self.ptbr.x() + d2
        h = rbr.y() + self.ptbr.y() + d2
        self.box.setRect(QtCore.QRectF(x, y, w - x, h - y))
        self.grid.set_length()

    def move(self):
        """Moving the whole region"""
        r = self.box.rect()
        x, y = r.x() + self.box.x(), r.y() + self.box.y()
        w, h = r.width(), r.height()
        d = self.ptul.width()
        d2 = d / 2
        self.ptul.setPos(x - d2, y - d2)
        self.ptbr.setPos(x + w - d2, y + h - d2)
        logging.debug('move:', x, y, w, h)
        self.grid.set_length()
