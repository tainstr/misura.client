#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Basic plot of an image profile path"""
from .. import _
from misura.client.widgets.active import *
import numpy as np
import cPickle as pickle
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)


class Profile(QtGui.QGraphicsView):
    
    def __init__(self, parent=None):
        QtGui.QGraphicsView.__init__(self, parent)
        self.scene = QtGui.QGraphicsScene(parent)
        self.path = False
        self.setScene(self.scene)

    def updateSize(self, sz):
        self.setMinimumSize(sz[0], sz[1])
        
    def clear(self):
        # Remove old path if present
        if self.path:
            self.scene.removeItem(self.path)
            self.path = False        

    def update(self, x, y):
        """Update graphics scene"""
        self.clear()
        # Discart malformed profiles
        if len(x) <= 1 or len(x) != len(y):
            logging.debug("Malformed profile", x,y)
            return
        # Scale
        x = np.array(x).astype(np.float32)
        x -= min(x)
        y = np.array(y).astype(np.float32)
        y -= min(y)
        x = 0.9*self.width()*x/max(x)
        y = 0.9*self.height()*y/max(y)
        # Convert x,y, vectors into a QPointF list
        lst = list(QtCore.QPointF(ix, y[i]) for i, ix in enumerate(x))
        # Create a QPainterPath and add a QPolygonF
        qpath = QtGui.QPainterPath()
        qpath.addPolygon(QtGui.QPolygonF(lst))
        # Add the path to the scene
        self.path = self.scene.addPath(qpath)


class aProfile(ActiveWidget):

    """Draws a profile property onto a rectangle."""

    def redraw(self):
        super(aProfile, self).redraw()
        self.profile = Profile(self)
        self.lay.addWidget(self.profile)
        self.emit(QtCore.SIGNAL('selfchanged()'))
        self.set_enabled()

    def set(self, *foo, **kfoo):
        """Override set() method in order to avoid forbidden write operations"""
        logging.debug("Set operation is not possible on Profile properties")

    def adapt2gui(self, val):
        """Unpickle profile data"""
        if getattr(val, 'data', False):
            val = pickle.loads(val.data)
        return val

    def update(self):
        """Update graphics scene"""
        prf = self.adapt2gui(self.current)
        if prf is None:
            logging.debug('No profile')
            return
        # Discart malformed profiles
        if len(prf) < 3:
            logging.debug("No profile", prf)
            return
        sz, x, y = prf
        # Discart malformed profiles
        if len(sz) < 2 or len(x) < 1 or len(x) != len(y):
            logging.debug( "Malformed profile", prf)
            return
        # Minimum dimension
        self.profile.updateSize(sz)
        self.profile.update(x, y)
