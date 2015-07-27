#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from active import *
from .. import _


class aBoolean(ActiveWidget):

    def __init__(self, server, path,  prop, parent=None):
        ActiveWidget.__init__(self, server, path,  prop, parent)
        self.chk = QtGui.QCheckBox(_('False'), parent=parent)
        self.lay.addWidget(self.chk)
        # Cause immediate update after complete init
        self.emit(QtCore.SIGNAL('selfchanged()'))
        if self.readonly:
            self.chk.setCheckable(False)
        else:
            self.connect(
                self.chk,  QtCore.SIGNAL('stateChanged(int)'), self.set)

    def adapt(self, val):
        if val in [0, '0', 'False', False, QtCore.Qt.Unchecked]:
            return False
        else:
            return True

    def update(self):
        if self.current:
            self.chk.setChecked(QtCore.Qt.Checked)
            self.chk.setText(_('True'))
            if self.handle == 'isRunning':
                self.chk.setStyleSheet("background-color:red; color:white;")
        else:
            self.chk.setChecked(QtCore.Qt.Unchecked)
            self.chk.setText(_('False'))
            if self.handle == 'isRunning':
                self.chk.setStyleSheet("background-color:green; color:white;")
        self.chk.update(self.chk.visibleRegion())


class aBooleanAction(QtGui.QAction):

    def __init__(self, remObj, prop, parent=None):
        QtGui.QAction.__init__(self, prop['name'], parent)
        self.setCheckable(True)
        QtGui.QAction.setChecked(self, prop['current'])
        self.remObj = remObj
        self.prop = prop
        self.handle = prop['handle']
        self.connect(self, QtCore.SIGNAL('hovered()'), self.get)
        self.connect(self, QtCore.SIGNAL('triggered(bool)'), self.set)
        if parent:
            self.connect(parent, QtCore.SIGNAL('aboutToShow()'), self.get)

    def get(self):
        r = self.remObj.get(self.handle)
        QtGui.QAction.setChecked(self, r)
        return r

    def set(self, val):
        self.remObj.set(self.handle, val)
        self.get()
