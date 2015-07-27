#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for image analysis"""
from PyQt4 import QtGui, QtCore

colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
          (0, 125, 125), (125, 125, 0), (125, 0, 125)] * 3
iflags = QtGui.QGraphicsItem.ItemIsSelectable | \
    QtGui.QGraphicsItem.ItemIsFocusable | QtGui.QGraphicsItem.ItemIsMovable


class HookItem(object):

    """A movable graphics point which calls hook functions each time it is moved on the scene"""
    hook = lambda foo: 0
    hookRelease = lambda foo: 0
    hookPress = lambda foo: 0

    def __init__(self, pen=False, Z=100, parent=None):
        self.setFlags(iflags)
        if pen == False:
            pen = QtGui.QPen(QtGui.QColor(*colors[0]))
            pen.setWidth(3)
        self.setPen(pen)
        self.setZValue(Z)
        self.setCursor(QtCore.Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        """Each time the point is moved, calls the hook function."""
        self.hook()
        return super(HookItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.hookRelease()
        return super(HookItem, self).mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        self.hook()
        self.hookPress()
        return super(HookItem, self).mousePressEvent(event)

    def width(self):
        return self.rect().width()

    def height(self):
        return self.rect().height()

    def unscale(self, factor):
        """Nullify zooming factor on Item's QPen"""
        f = 1. / factor
        p = self.pen()
        p.setWidthF(p.widthF() * f)
        self.setPen(p)


class HookPoint(HookItem, QtGui.QGraphicsEllipseItem):

    """Elliptical HookItem object, with cross cursor"""

    def __init__(self, x=0, y=0, w=0, h=0, pen=False, Z=100, parent=None):
        QtGui.QGraphicsEllipseItem.__init__(self, x, y, w, h, parent)
        HookItem.__init__(self, pen=False, Z=100, parent=None)


class HookRect(HookItem, QtGui.QGraphicsRectItem):

    """Rectangular HookItem object, with cross cursor"""

    def __init__(self, x=0, y=0, w=0, h=0, pen=False, Z=100, parent=None):
        QtGui.QGraphicsRectItem.__init__(self, x, y, w, h, parent)
        HookItem.__init__(self, pen=False, Z=100, parent=None)
