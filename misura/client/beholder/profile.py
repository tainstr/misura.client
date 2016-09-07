#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for image analysis"""
from misura.canon.logger import Log as logging
import numpy
from overlay import Overlay
from PyQt4 import QtGui, QtCore

def create_profile_points_for_hsm(rx, ry, rw, rh, xpt, ypt):
    lst = list(QtCore.QPointF(ix, ypt[i]) for i, ix in enumerate(xpt))
    lst.append(QtCore.QPointF(rx + rw, ry + rh))
    lst.append(QtCore.QPointF(rx, ry + rh))
    lst.append(QtCore.QPointF(xpt[0], ypt[0]))

    return lst

def create_profile_points_generic(rx, ry, rw, rh, xpt, ypt):
    lst = list(QtCore.QPointF(ix, ypt[i]) for i, ix in enumerate(xpt))

    return lst

class Profile(Overlay):

    """Draw a sequence of points corresponding to option type 'Profile'."""

    def __init__(self, parentItem, is_hsm, Z=2, profile_name='profile'):
        Overlay.__init__(self, parentItem, Z=Z)
        self.opt = set([profile_name, 'roi', 'crop'])
        self.profile_name = profile_name
        self.path = QtGui.QGraphicsPathItem(parent=self)
        self.path.setPen(self.pen)
        self.color.setAlpha(80)
        self.path.setBrush(QtGui.QBrush(self.color))
        self.create_profile_points = create_profile_points_generic
        if is_hsm:
            self.create_profile_points = create_profile_points_for_hsm

    def unscale(self, factor):
        Overlay.unscale(self, factor)
        self.path.setPen(self.pen)

    def up(self):
        """Update profile view"""
        if self.moving:
            return False
        if not self.current.has_key(self.profile_name):
            return
        prf = self.current[self.profile_name]
        if len(prf) < 3:
            logging.debug('%s %s', "No profile", prf)
            return False
        sz, x, y = prf
        # Discart malformed profiles
        if len(sz) < 2 or len(x) < 1 or len(x) != len(y):
            logging.debug('%s %s', "Malformed profile", prf)
            return False
        # Discart malformed profiles
        if len(x) <= 1 or len(x) != len(y):
            logging.debug('%s %s', "Malformed profile", prf)
            return False
        # Translate points with respect to sample ROI
        rx, ry, rw, rh = self.current['roi']
        self.xpt = numpy.array(x)  # +rx
        self.ypt = numpy.array(y)  # +ry
        profile_points = self.create_profile_points(rx, ry, rw, rh, self.xpt, self.ypt)

        # Create a QPainterPath and add a QPolygonF
        qpath = QtGui.QPainterPath()
        qpath.addPolygon(QtGui.QPolygonF(profile_points))
        qpath.setFillRule(QtCore.Qt.WindingFill)
        # Add the path to the scene
        self.path.setPath(qpath)
        return True
