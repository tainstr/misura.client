#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Display grid behind region of interest"""
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore


class Grid(object):
    """Display a grid behind a region of interest."""
    length = 100
    vertical = []
    horizontal = []
    enabled = False
    def __init__(self, region, Z=1, length = 100):
        self.region = region
        self.Z = Z
        self.length = length
        
    def set_enabled(self, val):
        self.enabled = val
        if val:
            self.set_length()
        else:
            self.cleanUp()
        
        
    def cleanUp(self):
        for item in self.horizontal+self.vertical:
            self.region.scene().removeItem(item)
        self.horizontal = []
        self.vertical = []
        
    
    def set_length(self, val=-1):
        if not self.enabled:
            return
        if val<0:
            val = self.length
        else:
            self.length = int(val)
        self.cleanUp()
        
        box = self.region.box
        rect = box.rect()
        bx = rect.x()
        by = rect.y()
        
        pen = QtGui.QPen()
        col = self.region.pen.color()
        col.setAlpha(128)
        pen.setColor(col)
        pen.setStyle(QtCore.Qt.SolidLine)
        pen.setWidth(int(self.region.pen.width()*0.8))
        
        def mkline(x0,y0,x1,y1):
            line = QtGui.QGraphicsLineItem(x0, y0, x1, y1, box)
            line.setPen(pen)
            line.setZValue(self.Z)
            return line           
        
        
        for i in range(int(box.width()/self.length)+1):
            x = self.length*i + bx
            line = mkline(x, by, x, by+box.height())
            self.vertical.append(line)
            
        for i in range(int(box.height()/self.length)+1):
            y = self.length*i + by
            line = mkline(bx, y, bx+box.width(), y)
            self.horizontal.append(line)           
        
        return self.length