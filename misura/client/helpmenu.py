#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui, QtCore
from . import _
from misura.client.confwidget import ClientConf
from misura.client.live import registry

class HelpMenu():

	def add_help_menu(self):
		self.help = self.addMenu('Help')
		self.help.addAction(_('Client configuration'), self.showClientConf)
		self.help.addAction(_('Documentation'), self.showDocSite)
		self.help.addAction(_('Pending operations'), self.showTasks)

	def hide_help_menu(self):
		self.help.menuAction().setVisible(False)


	def showClientConf(self):
		"""Show client configuration panel"""
		self.cc = ClientConf()
		self.cc.show()

	def showDocSite(self):
		url = 'http://misura.readthedocs.org'
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

	def showTasks(self):
		registry.taskswg.user_show = True
		registry.taskswg.show()
