#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Results tab with access to data tools"""
from .. import navigator
from .. import _
from veusz.windows import treeeditwindow
from veusz.windows import consolewindow

from PyQt4 import QtGui, QtCore

class Results(QtGui.QTabWidget):

    def __init__(self, parent, plot):
        super(Results, self).__init__(parent)
        self.setTabPosition(QtGui.QTabWidget.North)
        self.plot = plot
        
        self.navigator = navigator.Navigator(
            parent=self, mainwindow=plot, cols=1)
            
        self.plot.connect(
            self.plot, QtCore.SIGNAL('hide_show(QString)'), self.navigator.plot)

    def set_doc(self, doc):
        self.clear()
        te = self.plot.treeedit
        self.props = treeeditwindow.PropertiesDock(doc, te, self)
        self.props.setWindowTitle(_('No selection'))
        self.formats = treeeditwindow.FormatDock(doc, te, self)
        self.formats.setWindowTitle(_('No selection'))
        self.console = consolewindow.ConsoleWindow(doc, self)
        self.console.checkVisible = lambda *disableCheckVisible: None


        self.addTab(self.navigator, _('Data'))
        self.addTab(self.props, _('Properties'))
        self.addTab(self.formats, _('Formatting'))
        self.addTab(self.plot.treeedit, _('Objects'))
        self.addTab(self.console, _('Console'))
        
        self.plot.plot.sigWidgetClicked.connect(self.slot_selected_widget)
        
    def slot_selected_widget(self, *foo):
        name = _('For: ')+self.navigator.cmd.currentwidget.name
        self.props.setWindowTitle(name)
        self.formats.setWindowTitle(name)