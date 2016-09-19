#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Results tab with access to data tools"""
from .. import navigator

from veusz.windows import treeeditwindow
from veusz.windows import consolewindow

from PyQt4 import QtGui, QtCore

class Results(QtGui.QTabWidget):

    def __init__(self, parent, plot):
        super(Results, self).__init__(parent)
        self.setTabPosition(QtGui.QTabWidget.North)
        self.plot = plot
        
        self.navigator = navigator.Navigator(
            parent=self, mainwindow=plot, cols=2)
            
        self.plot.connect(
            self.plot, QtCore.SIGNAL('hide_show(QString)'), self.navigator.plot)

    def set_doc(self, doc):
        self.clear()
        te = self.plot.treeedit
        self.props = treeeditwindow.PropertiesDock(doc, te, self)
        self.formats = treeeditwindow.FormatDock(doc, te, self)

        self.console = consolewindow.ConsoleWindow(doc, self)
        self.console.checkVisible = lambda *disableCheckVisible: None


        self.addTab(self.navigator, 'Data')
        self.addTab(self.props, 'Properties')
        self.addTab(self.formats, 'Formatting')
        self.addTab(self.plot.treeedit, 'Objects')
        self.addTab(self.console, 'Console')

        #self.navigator.resizeColumnToContents(0)