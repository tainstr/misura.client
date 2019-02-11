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
        # Default sorting on column DATE, descending
        self.setSortIndicator(4, 0)
        

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
            self.showSection(i)
        else:
            self.hideSection(i)
