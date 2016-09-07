#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for border image analysis"""
from misura.canon.logger import Log as logging
from overlay import Overlay
from PyQt4 import QtGui


class ReferenceLine(Overlay):

    def __init__(self, parentItem, Z=1, startLine=True):
        Overlay.__init__(self, parentItem, Z=Z)
        self.opt = set(
            ['startLine', 'slope', 'const', 'domain', 'roi', 'crop'])
        # Create base and height lines
        self.line = QtGui.QGraphicsLineItem(parent=self)
        if not startLine:
            self.pen.setColor(QtGui.QColor('red'))
        self.line.setPen(self.pen)
        self.startLine = startLine

    def unscale(self, factor):
        Overlay.unscale(self, factor)
        self.line.setPen(self.pen)

    def up(self):
        if self.moving:
            return False
        if len(self.current['startLine']) != 3:
            return False
        
        if self.startLine:
            slope, const, domain = self.current['startLine']
        else:
            slope = self.current['slope']
            const = self.current['const']
            domain = self.current['domain']
            
        rx, ry, w, h = self.current['roi']
        
        if domain == 1:  # x=slope*y + const
            self.line.setLine(0, const, w, const + slope * w)
        else:
            self.line.setLine(const, 0, const + slope * h, h)
        return True
