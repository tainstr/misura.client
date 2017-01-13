#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore
from time import sleep
import hook


class SensorPlane(QtGui.QGraphicsItem):

    def __init__(self, remote, parent=None):
        QtGui.QGraphicsItem.__init__(self, parent=parent)
        self.setZValue(-1)
        self.remote = remote
        # Current sensor position box
        res = self.remote['resolution']
        self.box = QtGui.QGraphicsRectItem(0, 0, res[0], res[1], parent=self)
        self.box.setBrush(QtCore.Qt.gray)
        # Region handler
        self.pt = hook.HookRect(-5, -5, 10, 10, parent=self)
        self.pt.setFlag(QtGui.QGraphicsItem.ItemIgnoresTransformations, True)
        self.pt.hookPress = self.motion_start
        self.pt.hookRelease = self.motion_stop
        self.pt.hook = self.motion_preview
        # Motion preview box
        self.pre = QtGui.QGraphicsRectItem(0, 0, 0, 0, parent=self)
        self.pre.setPen(self.pt.pen())
        self.pre.hide()

        # Cropped region
        self.cropBox = QtGui.QGraphicsRectItem(
            0, 0, res[0], res[1], parent=self)
        self.cropBox.setBrush(QtCore.Qt.darkGray)
        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setStyle(QtCore.Qt.DotLine)
        self.cropBox.setPen(pen)

        self.m_start = (0, 0)
        self.m_stop = (0, 0)
        self.moving = {'x': 0, 'y': 0}
        self.align = 1.
        self.timer = QtCore.QTimer()
        self.timer.setInterval(200)
        self.timer.connect(
            self.timer, QtCore.SIGNAL('timeout()'), self.motion_update)

    def paint(self, *a, **kw):
        return None

    def unscale(self, factor):
        f = 1. / factor
        pen = self.pre.pen()
        w = pen.widthF() * f
        logging.debug('%s %s %s %s', 'Rescaling pens to ', w, factor, f)
        pen.setWidthF(w)
        self.pre.setPen(pen)
        pen = self.cropBox.pen()
        pen.setWidth(w)
        self.cropBox.setPen(pen)

    def set_crop(self, x, y, w, h):
        self.cropBox.setRect(x, y, w, h)

    def boundingRect(self):
        return self.box.boundingRect()

    def enc(self, coord):
        """Return remote encoder proxy for `coord`"""
        return getattr(self.remote.encoder, coord, None)

    def pos(self, coord=None, new=None):
        """Return/set the pixel position"""
        if coord is None:
            return self.pos('x'), self.pos('y')
        inv = self.remote.encoder['invert']
        if inv:
            coord = {'x': 'y', 'y': 'x'}.get(coord, coord)
        else:
            inv = 1.
        enc = getattr(self.remote.encoder, coord, None)
        if enc is None:
            return 0
        logging.debug(
            '%s %s %s %s', 'encoder coord is', coord, enc['align'], inv)
        self.align = inv * 1. * enc['align']
        mp = enc['motor'][0]
        m = self.remote.root.toPath(mp)
        if m in [None, False, 'None'] or m._Method__name == None or mp in ['None', None]:
            return 0
        logging.debug(
            '%s %s %s %s %s %s', 'GOT MOTOR', coord, mp, m, type(m), m._Method__name)
        if new is None:
            # Return pixel position
            self.moving[coord] = m['moving']
            return 1. * m['position'] * self.align
        m['goingTo'] = new / self.align
        self.moving[coord] = 1
        logging.debug(
            '%s %s %s %s', 'moving to', new / self.align, new, self.align)
        return new

    def motion_start(self):
        """Take starting coordinates"""
        self.m_start = self.pos('x'), self.pos('y')
        r = self.boundingRect()
        self.pre.setRect(0, 0, r.width(), r.height())
        self.pre.show()
        self.setCursor(QtCore.Qt.ClosedHandCursor)
        logging.debug(
            '%s %s %s %s', 'motionStart', self.m_start, self.x(), self.y())

    def motion_update(self):
        """Called periodically while the motor is moving"""
        sleep(0.1)
        x0, y0 = self.m_start
        x1, y1 = self.m_stop
        x, y = self.pos()
        dx0 = x - x0
        dy0 = y - y0
        dx1 = x1 - x
        dy1 = y1 - y
        logging.debug(
            '%s %s %s %s %s %s %s %s %s', 'motion_update', x0, x, x1, y0, y, y1, dx0, dx1)
        self.setPos(-dx0, -dy0)
        self.pre.setPos(-dx1, -dy1)
        self.pt.setPos(-dx1, -dy1)

        if self.moving['x'] + self.moving['y'] == 0:
            self.timer.stop()
            self.pre.hide()
            self.setCursor(QtCore.Qt.ArrowCursor)
            logging.debug('%s %s', 'TIMER STOP', self.moving)
            self.pt.setPos(0, 0)
            self.setPos(0, 0)
            self.pt.ensureVisible()

    def motion_stop(self):
        """Take target coordinates."""
        x, y = self.m_start
        # Relative position with respect to the middle of the point
        dx = (self.pt.x())
        dy = (self.pt.y())
        logging.debug('%s %s %s %s %s', 'motion_stop', x, dx, y, dy)
        x -= dx
        y -= dy
        self.pos('x', x)
        self.pos('y', y)
        self.m_stop = x, y
        self.timer.start()
        self.setCursor(QtCore.Qt.BusyCursor)
        logging.debug(
            '%s %s %s %s', 'motionStop', self.m_stop, dx / self.align, dy / self.align)

    def motion_preview(self):
        # TODO: show preview labels
        # 		x,y=self.m_start
        dx = (self.pt.x())
        dy = (self.pt.y())
        self.pre.setPos(dx, dy)
        self.pt.ensureVisible()
# 		print 'motionPreview',x-dx,y-dy
