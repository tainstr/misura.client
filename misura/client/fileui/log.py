#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Logged data visualization"""
from .. import _
from PyQt4 import QtGui


class OfflineLog(QtGui.QTextEdit):
	"""Simple text window displaying static log messages recorded in a file"""
	def __init__(self, proxy, parent=None):
		QtGui.QTextEdit.__init__(self, parent)
		self.setReadOnly(True)
		self.setLineWrapMode(self.NoWrap)
		self.label=_('Log')
		self.menu=QtGui.QMenu(self)
		self.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
		self.proxy=proxy
		self.setPlainText(proxy.getLog())