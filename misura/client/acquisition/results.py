#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Results tab with access to data tools"""
from PyQt4 import QtGui, QtCore
from .. import widgets

class Results(QtGui.QTabWidget):
	def __init__(self,parent):
		super(Results,self).__init__(parent)
		self.setTabPosition(QtGui.QTabWidget.East)
		
		