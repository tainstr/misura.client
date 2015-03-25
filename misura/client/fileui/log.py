#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Logged data visualization"""
from misura.client import widgets
from PyQt4 import QtGui


class OfflineLog(QtGui.QTextEdit, widgets.Linguist):
	"""Simple text window displaying static log messages recorded in a file"""
	def __init__(self, proxy, parent=None):
		QtGui.QTextEdit.__init__(self, parent)
		widgets.Linguist.__init__(self, 'Local')
		self.setReadOnly(True)
		self.setLineWrapMode(self.NoWrap)
		self.label=self.mtr('Log')
		self.menu=QtGui.QMenu(self)
		self.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
		self.proxy=proxy
		self.setPlainText(proxy.getLog())