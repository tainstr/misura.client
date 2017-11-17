#!/usr/bin/python
# -*- coding: utf-8 -*-

from misura.client.widgets.active import QtGui, QtCore, ActiveWidget
from .. import _


class aString(ActiveWidget):

    """Graphical element for interacting with a text string"""
    
    def __init__(self, server, path,  prop, parent=None, extended=False):
        self.extended = extended
        ActiveWidget.__init__(self, server, path,  prop, parent)
    
    def redraw(self):
        super(aString, self).redraw()
        if self.extended:
            self.browser = QtGui.QTextBrowser()
            self.signal = 'textChanged()'
        else:
            self.browser = QtGui.QLineEdit("")
            self.signal = 'textChanged(QString)'
        
        super(aString, self).redraw()
        self.browser.setReadOnly(self.readonly)
        self.connect(self.browser,   QtCore.SIGNAL(self.signal), self.text_updated)
        self.lay.addWidget(self.browser)
        self.emit(QtCore.SIGNAL('selfchanged()'))
        self.set_enabled()

    def adapt(self, val):
        """Enforce unicode everywhere"""
        return unicode(val)

    def adapt2gui(self, val):
        """Returns a QString ready for the GUI"""
        return unicode(val)

    def adapt2srv(self, val):
        """Converts everything to unicode"""
        return unicode(val)

    def update(self):
        self.disconnect(self.browser, QtCore.SIGNAL(self.signal), self.text_updated)
        val = self.adapt(self.current)
        self.readonly_label.setText(val)
        if self.extended:
            self.browser.setPlainText(val)
        else:
            self.browser.setText(val)
        if self.readonly:
            self.browser.setReadOnly(True)
            self.browser.hide()
            self.readonly_label.show()
        else:
            self.browser.setReadOnly(False)
            self.browser.show()
            self.readonly_label.hide()
        self.connect(self.browser,   QtCore.SIGNAL(self.signal), self.text_updated)
        

    def text_updated(self, *foo):
        if self.extended:
            self.current = self.browser.toPlainText()
        else:
            self.current = self.browser.text()
        self.remObj.set(self.handle, self.current)
        

    def emitOptional(self):
        #       print 'textEdited(QString)', self.current
        self.emit(QtCore.SIGNAL('textEdited(QString)'), self.current)
