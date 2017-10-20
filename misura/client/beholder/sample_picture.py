#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore
from traceback import format_exc
import functools

import region
import profile
import shape
import border
from overlay import Overlay


def is_hsm_sample(sample):
    r='/hsm/' in sample['fullpath']
    return r

class MetaItem(QtGui.QGraphicsSimpleTextItem):

    def contextMenuEvent(self, event):
        self.parentItem().contextMenuEvent(event)

    @property
    def menu(self):
        return self.parentItem().menu


class MetaLabel(Overlay):

    """Metadata label visualization"""

    def __init__(self, parentItem, Z=1):
        Overlay.__init__(self, parentItem, Z)
        self.label = MetaItem(parent=self)
        self.label.setText('Empty')
        self.label.setFlags(QtGui.QGraphicsItem.ItemIsSelectable |
                            QtGui.QGraphicsItem.ItemIsFocusable | QtGui.QGraphicsItem.ItemIsMovable |
                            QtGui.QGraphicsItem.ItemIgnoresTransformations)
        self.menu = QtGui.QMenu()
        self.acts = {}

    def unscale(self, factor):
        Overlay.unscale(self, factor)
        self.up()

    def up(self):
        t = ''
        for k, v in self.current.iteritems():
            t += '{}: {:.2e}\n'.format(k, v)
        if len(t) == 0:
            t = 'Empty'
        logging.debug('updating to', t, 'MetaLabels')
        self.label.setText(t)

    def add(self, name):
        logging.debug('adding name', name)
        self.opt.add(name)
        rem = functools.partial(self.remove, name)
        a = self.menu.addAction(name, rem)
        a.setCheckable(True)
        a.setChecked(True)
        self.acts[name] = a, rem
        self.parentItem().parentItem().opt_changed = True

    def remove(self, name):
        logging.debug('removing name', name)
        self.opt.remove(name)
        del self.current[name]
        self.menu.removeAction(self.acts[name][0])


class SamplePix(QtGui.QGraphicsPixmapItem):

    def __init__(self, *a, **k):
        QtGui.QGraphicsPixmapItem.__init__(self, *a, **k)
        self.setAcceptDrops(True)
        self.label = MetaLabel(self)

    def unscale(self, factor):
        self.label.unscale(factor)

    def dragEnterEvent(self, event):
        logging.debug('dragEnterEvent', event.mimeData())
        event.acceptProposedAction()
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        logging.debug('DROP EVENT')
        opt = str(event.mimeData().text()).replace(
            'summary', '').replace('//', '/').split('/')[-1]
        logging.debug('Adding option:', opt)
        self.label.add(opt)
        self.parentItem().opt_changed = True

class SamplePicture(QtGui.QGraphicsItem):

    """Graphical item representing a Sample, including its image and all overlays describing geometry data"""
    overlays = []
    opt_changed = False

    def __init__(self, parentItem, smp, n):
        """`parentItem`: parent graphical item
        `smp`; remote sample object
        `n`: graphical Z layer"""
        QtGui.QGraphicsItem.__init__(self, parent=parentItem)
        self.smp = smp
        self.pixItem = SamplePix(parent=self)
        self.pix = self.pixItem.pixmap()
        self.pixItem.show()
        self.overlays = []


        # General
        # BoxRegion must have same parent as self (sensorplane)
        self.roi = region.BoxRegion(parentItem, self.smp, Z=n)
        self.overlays.append(self.roi)
        
        self.is_hsm = is_hsm_sample(smp)
        self.profile = profile.Profile(parentItem, self.is_hsm)
        self.overlays.append(self.profile)
        
        self.label = self.pixItem.label
        self.overlays.append(self.label)
        # TODO: distinguish instrument overlays based on mro!
        umpx = smp.analyzer['umpx']
        # Shape-specific
        if self.is_hsm:
            self.points = shape.SamplePoints(parentItem)
            self.overlays.append(self.points)
            self.baseHeight = shape.BaseHeight(parentItem, umpx=umpx)
            self.overlays.append(self.baseHeight)
            self.circle = shape.CircleFit(parentItem, umpx=umpx)
            self.overlays.append(self.circle)
        else:
            self.referenceLine = border.ReferenceLine(parentItem, startLine=True)
            self.overlays.append(self.referenceLine)
            
            self.regressionLine = border.ReferenceLine(parentItem, startLine=False)
            self.overlays.append(self.regressionLine)
            
            self.filteredProfile = profile.Profile(parentItem, False, profile_name='filteredProfile')
            self.overlays.append(self.filteredProfile)


        self.show()

    def boundingRect(self):
        return self.pixItem.boundingRect()

    def close(self):
        for ov in self.overlays:
            ov.hide()
            self.scene().removeItem(ov)
            del ov

    def unscale(self, factor):
        for ov in self.overlays:
            ov.unscale(factor)
        self.pixItem.unscale(factor)

    def update(self, multiget):
        """Update all visible overlay with new dictionary"""
        if len(multiget) == 0:
            return False
        roi = multiget.get('roi', False)
        if roi:
            x, y = roi[:2]
            if x < 0:
                x = 0
            if y < 0:
                y = 0
            self.setPos(x, y)
        for ov in self.overlays:
            if ov.isVisible():
                try:
                    ov.slot_update(multiget)
                except:
                    logging.debug('Overlay update error')
                    logging.debug(format_exc())
        return True

    @property
    def opt(self):
        """Return the set of all required options for overlay update"""
        r = set([])
        for ov in self.overlays:
            if not ov.isVisible():
                continue
            r = r.union(ov.opt)
        return r

    @opt.setter
    def opt(self, val):
        """Allow to reset opt by setting it to []"""
        assert val == []
        for ov in self.overlays:
            ov.hide()

    def paint(self, *a, **kw):
        return None
