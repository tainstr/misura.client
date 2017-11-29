#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from .. import _
from PyQt4 import QtGui

def informative_message_box(r, parent=None, limit=200):
    r1 = r
    more = False
    if len(str(r)) > limit:
        more = True
        r = r[:limit-10] + '...'
    msg = QtGui.QMessageBox(parent=parent)
    msg.setWindowTitle(_('Operation Result'))
    msg.setWindowFlags(QtCore.Qt.Dialog)
    msg.setInformativeText(str(r))
    if more:
        msg.setDetailedText(r1)
    
    return msg  

class aButton(ActiveWidget):
    get_on_enter = False
    get_on_leave = False
    """Do not auto-update when mouse enters."""

    def __init__(self, server, path,  prop, parent=None):
        ActiveWidget.__init__(self, server, path,  prop, parent)
        self.button = QtGui.QPushButton(self.tr(self.name))
        self.connect(self.button,  QtCore.SIGNAL('pressed()'), self.async_get)
        self.lay.addWidget(self.button)
        self.set_enabled()
        self.connect(
            self, QtCore.SIGNAL('changed()'), self.show_msg, QtCore.Qt.QueuedConnection)

    def _msgBox(self):
        """Generate message box for display"""
        r = self.current
        if r is True:
            r = _('Done')
        elif r is False:
            r = _('Failed')
        msg = informative_message_box(r, self)
        msg.setText(_('Result for option "{}"').format(self.prop['name']))
        return msg
        
        
    def show_msg(self):
        """Display informative messagebox"""
        msgBox = self._msgBox()
        return msgBox.exec_()
