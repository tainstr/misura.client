#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for sample shape image analysis"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from overlay import Overlay
from PyQt4 import QtGui


class SamplePoints(Overlay):

    def __init__(self, parentItem, Z=1):
        Overlay.__init__(self, parentItem, Z=Z)
        self.opt = set(['profile', 'iA', 'iB', 'iC', 'iD', 'roi', 'crop'])
        # Create Points attributes, iA, iB, etc
        for p in self.opt:
            if not p.startswith('i'):
                continue
            g = QtGui.QGraphicsEllipseItem(parent=self)
            g.setPen(self.pen)
            g.setZValue(self.Z)
            g.setPos(0, 0)
            setattr(self, p, g)

    def unscale(self, factor):
        Overlay.unscale(self, factor)
        self.iA.setPen(self.pen)
        self.iB.setPen(self.pen)
        self.iC.setPen(self.pen)
        self.iD.setPen(self.pen)

    def up(self):
        if self.moving:
            return False
        sz, vx, vy = self.current['profile']
        nx, ny = len(vx), len(vy)
        rx, ry, rw, rh = self.current['roi']
        cx, cy, cw, ch = self.current.get('crop', [rx, ry, rw, rh])
        logging.debug('updating points', self.current.keys(), rx, cx, ry, cy)
        d = 10
        d = int(self.dim(factor=75, minimum=12)) + 1  # pt diameter
        d2 = d / 2
        for p in ['iA', 'iB', 'iC', 'iD']:
            i = self.current.get(p, 0)
            if i >= nx or i >= ny:
                logging.debug('Invalid point', p, i, nx, ny)
                return False
            logging.debug(p, i)
            x = vx[i]  # -rx+cx
            y = vy[i]  # -ry+cy
            g = getattr(self, p)
            g.setRect(x - d2, y - d2, d, d)
        return True


class BaseHeight(Overlay):

    def __init__(self, parentItem, Z=1, umpx=1):
        Overlay.__init__(self, parentItem, Z=Z)
        self.opt = set(
            ['profile', 'iA', 'roi', 'angle', 'w', 'h', 'xmass', 'ymass', 'crop'])
        # Create base and height lines
        self.base = QtGui.QGraphicsLineItem(parent=self)
        self.base.setPen(self.pen)
        self.height = QtGui.QGraphicsLineItem(parent=self)
        self.height.setPen(self.pen)
        self.umpx = umpx
        
    def unscale(self, factor):
        Overlay.unscale(self, factor)
        self.base.setPen(self.pen)
        self.height.setPen(self.pen)     

    def up(self):
        if self.moving:
            return False
        self.setRotation(0)
        sz, x, y = self.current['profile']
        rx, ry, rw, rh = self.current['roi']
        cx, cy, cw, ch = self.current.get('crop', [rx, ry, rw, rh])
        i = self.current.get('iA', 0)
        a = self.current.get('angle', 0)
        w = self.current.get('w', 0)/self.umpx
        h = self.current.get('h', 0)/self.umpx
        x = x[i]  # +rx-cx
        y = y[i]  # +ry-cy
        self.base.setLine(x, y, x + w, y)
        self.height.setLine(x, y, x, y - h)
        self.setTransformOriginPoint(x, y)
        self.setRotation(a)
        return True


class CircleFit(Overlay):

    def __init__(self, parentItem, Z=1, umpx=1):
        Overlay.__init__(self, parentItem, Z=Z)
        self.opt = set(['xmass', 'ymass', 'radius', 'angle'])
        self.circle = QtGui.QGraphicsEllipseItem(parent=self)
        self.circle.setPen(self.pen)
        self.circle.setPos(0, 0)
        self.umpx = umpx

    def up(self):
        if self.moving:
            return False
        x = self.current['xmass']
        y = self.current['ymass']
        r = self.current['radius'] / self.umpx
        self.circle.setRect(x - r, y - r, 2 * r, 2 * r)
        return True
