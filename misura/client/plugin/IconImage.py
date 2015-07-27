#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Special Widget"""
import veusz.plugins as plugins
from PyQt4 import QtGui, QtCore
import veusz.widgets
import veusz.document as document
import veusz.utils
import os
from misura.canon.logger import Log as logging


class IconImage(veusz.widgets.ImageFile):
    typename = 'iconimage'
    description = 'Icon image'
    allowusercreation = True

    def __init__(self, parent, name=None):
        veusz.widgets.ImageFile.__init__(self, parent, name=name)
        self.cachewidth = 0
        self.cacheheight = 0

    @classmethod
    def _addSettings(klass, s):
        """Construct list of settings."""
        lst = ['None'] + veusz.utils.action._iconcache.keys()
        lst.sort()
        logging.debug('%s', lst)
        s.add(veusz.setting.Choice('iconname',
                                   lst,
                                   'None',
                                   descr='Icon name',
                                   usertext='IconName'),
              posn=0)
        s.add(veusz.setting.Bool('aspect', True,
                                 descr='Preserve aspect ratio',
                                 usertext='Preserve aspect',
                                 formatting=True),
              posn=0)

    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        veusz.widgets.BoxShape.addSettings(s)
        klass._addSettings(s)
#		lst=['None']+veusz.utils.action._iconcache.keys()
#		lst.sort()
#		print lst
#		s.add( veusz.setting.Choice('iconname',
#									lst,
#									'None',
#									 descr='Icon name',
#									 usertext='IconName'),
#				posn=0 )
#		s.add( veusz.setting.Bool('aspect', True,
#							descr='Preserve aspect ratio',
#							usertext='Preserve aspect',
#							formatting=True),
#				posn=0 )
        s.Border.get('hide').newDefault(True)

    def updateCachedPixmap(self, w=16, h=16):
        """Update cache."""
        s = self.settings
        self.cachestat = os.stat('.')
        icon = veusz.utils.action._iconcache[s.iconname]
        self.cachepixmap = icon.pixmap(w, h)
        self.cachefilename = s.iconname
        self.cachewidth = w
        self.cacheheight = h
        return self.cachepixmap

    def drawShape(self, painter, rect):
        """Draw pixmap."""
        s = self.settings
        # draw border and fill
        painter.drawRect(rect)
        # cache pixmap
        w, h = rect.width(), rect.height()
        if self.cachefilename != s.iconname or w != self.cachewidth or h != self.cacheheight:
            self.updateCachedPixmap(w, h)
        pixmap = self.cachepixmap
        # pixmap rectangle
        prect = QtCore.QRectF(pixmap.rect())
        logging.debug('%s', prect)
#		# preserve aspect ratio
        if s.aspect:
            xr = rect.width() / prect.width()
            yr = rect.height() / prect.height()

            if xr > yr:
                rect = QtCore.QRectF(rect.left() + (rect.width() -
                                                    prect.width() * yr) * 0.5,
                                     rect.top(),
                                     prect.width() * yr,
                                     rect.height())
            else:
                rect = QtCore.QRectF(rect.left(),
                                     rect.top() + (rect.height() -
                                                   prect.height() * xr) * 0.5,
                                     rect.width(),
                                     prect.height() * xr)

        # finally draw pixmap
        painter.drawPixmap(rect, pixmap, prect)

document.thefactory.register(IconImage)
