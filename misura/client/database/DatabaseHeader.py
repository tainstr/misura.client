#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import functools


class DatabaseHeader(QtGui.QHeaderView):

    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None):
        QtGui.QHeaderView.__init__(self, orientation, parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.show_menu)
        self.menu = QtGui.QMenu(self)
        self.setMovable(True)
        self.setClickable(True)
        self.setSortIndicatorShown(True)
        

    def show_menu(self, pt):
        QtGui.qApp.processEvents()
        self.menu.clear()
        for i, h in enumerate(self.model().sheader):
            act = self.menu.addAction(h, functools.partial(self.switch, i))
            act.setCheckable(True)
            act.setChecked((not self.isSectionHidden(i)) * 2)
        self.menu.popup(self.mapToGlobal(pt))

    def switch(self, i):
        if self.isSectionHidden(i):
            logging.debug('showSection', i, self.model().header[i])
            self.showSection(i)
        else:
            logging.debug('hideSection', i, self.model().header[i])
            self.hideSection(i)
            
    def show_all_sections(self):
        for sec in xrange(len(self.model().header)):
            logging.debug('Showing section', self.model().header[sec], sec)
            self.setSectionHidden(sec, False)
        self.reset()
            
    def hide_sections(self, sections):
        self.show_all_sections()
        for sec in sections:
            n = self.model().ncol(sec)
            if n<0:
                continue
            logging.debug('Hiding section', sec, n)
            self.setSectionHidden(n, True)
            
    def restore_visual_indexes(self):
        for i in xrange(len(self.model().header)):
            j = self.visualIndex(i)
            if i!=j:
                self.moveSection(i,j)
                
    def visibility(self):
        ret = []
        for sec in xrange(len(self.model().header)):
            ret.append(self.isSectionHidden(sec))
        return ret