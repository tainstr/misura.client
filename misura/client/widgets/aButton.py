#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from PyQt4 import QtGui

class aButton(ActiveWidget):
	def __init__(self, server, path,  prop, parent=None):
		ActiveWidget.__init__(self, server,path,  prop, parent)
		self.button=QtGui.QPushButton(self.tr(self.name))
		self.connect(self.button,  QtCore.SIGNAL('pressed()'), self.get)
		self.lay.addWidget(self.button)
		self.connect(self, QtCore.SIGNAL('changed()'), self.msg)
		
	def msg(self):
		r=self.current
		if r is True: r=_('Done')
		elif r is False: r=_('Failed')
		QtGui.QMessageBox.information(self, _('Operation Result'), str(r))
			
	def enterEvent(self, event):
		"""Override auto-update when mouse enters."""
		return None
