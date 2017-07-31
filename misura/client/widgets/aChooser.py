#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from ..iutils import theme_icon
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore
from misura.client.widgets.active import ActiveWidget


class aChooser(ActiveWidget):
    tuplelike = False
    """If data passed to combobox are tuple, they must be converted into list an back"""

    def __init__(self, server, path, prop, parent=None):
        ActiveWidget.__init__(self, server, path,  prop, parent)
        self.combo = QtGui.QComboBox(parent=self)
        self._options = []
        self._values = []
        self.changed_option(reget=False)
        self.lay.addWidget(self.combo)
        self.connect(
            self.combo,  QtCore.SIGNAL('currentIndexChanged(int)'), self.try_set)

    def enterEvent(self, event):
        """Update the widget anytime the mouse enters its area.
        This must be overridden in one-shot widgets, like buttons."""
        if self.type == 'FileList':
            self.changed_option()
        else:
            self.get()
            self.changed_option()
        return ActiveWidget.enterEvent(self, event)

    def try_set(self, idx):
        result = self.set(idx)
        new_idx = self.adapt2gui(result)
        if new_idx != idx:
            self.changed_option()

    def changed_option(self, reget=True):
        # Get new property
        super(aChooser, self).changed_option()
        opt = self.prop.get('options', [])
        vals = self.prop.get('values', opt)
        if opt == self._options or vals == self._values:
            logging.debug('No update needed')
            return False
        self.combo.blockSignals(True)
        # Cleans combo entries
        self.combo.clear()
        # Associate opt-val couples to new combo entries
        for i in range(len(opt)):
            k = opt[i]
            v = vals[i]
            if isinstance(v, tuple):
                self.tuplelike = True
                v = list(v)
            if type(k) == type(''):
                k = self.tr(k)
            elif type(k) != type(u''):
                k = str(k)
                K = self.tr(k)
            self.combo.addItem(k, v)
        # Read again the current options, if requested
        if reget:
            self.get()
        self.update()
        self._options = opt
        self._values = vals
        # Restore signals
        self.combo.blockSignals(False)
        return True

    def adapt2srv(self, idx):
        """Translates combobox index into server value"""
        r = self.combo.itemData(idx)
        if isinstance(r, str):
            r = str(r)
        elif self.tuplelike:
            r = tuple(r)
        logging.debug('adapt2srv', idx, r)
        return r

    def adapt2gui(self, val):
        """Translates server value into corresponding combobox index"""
        if self.tuplelike:
            val = list(val)
        r = self.combo.findData(val)
        return r

    def update(self):
        self.combo.blockSignals(True)
        idx = self.adapt2gui(self.current)
        self.combo.setCurrentIndex(self.adapt2gui(self.current))
        self.combo.blockSignals(False)


class async_aChooser(aChooser):

    def __init__(self, server, path, prop, parent=None):
        aChooser.__init__(self, server, path,  prop, parent)

    def set(self, val, *foo):
        """Set a new value `val` to server. Convert val into server units."""
        val = self.adapt2srv(val)
        if val == self.current:
            logging.debug('Not setting', self.handle, repr(val))
            return True

        QtCore.QTimer.singleShot(0, lambda: self.remObj.set(self.handle, val))
        return self.get()

class FurnacePositionChooser(async_aChooser):
    def __init__(self, server, path, prop, parent=None):
        self.btn_open = QtGui.QPushButton(u"\U0001F513")
        #self.btn_open.setIcon(theme_icon('go-next'))
        
        self.btn_open.clicked.connect(self.go_open)
        self.btn_open.setMaximumWidth(50)
        
        self.btn_close = QtGui.QPushButton(u"\U0001F512")
        #self.btn_close.setIcon(theme_icon('go-previous'))
        self.btn_close.clicked.connect(self.go_close)
        self.btn_close.setMaximumWidth(50)
        
        self.btn_pause = QtGui.QPushButton()
        self.btn_pause.setIcon(theme_icon('media-playback-pause'))
        self.btn_pause.clicked.connect(self.go_pause)
        self.btn_pause.setMaximumWidth(50)
        
        async_aChooser.__init__(self, server, path, prop, parent=parent)

        
    def go_open(self):
        QtCore.QTimer.singleShot(0, lambda: self.remObj.set(self.handle, 0))
    
    def go_close(self):
        QtCore.QTimer.singleShot(0, lambda: self.remObj.set(self.handle, 1))
        
    def go_pause(self):
        self.remObj.set(self.handle, 3)
            
    def changed_option(self, *a, **k):
        r = async_aChooser.changed_option(self, *a, **k)
        if self.current!=-1:
            if self.lay.indexOf(self.btn_open)==-1 or self.lay.indexOf(self.btn_open)==-1:
                self.lay.addWidget(self.btn_open)
                self.lay.insertWidget(0, self.btn_close)
                self.lay.insertWidget(1, self.btn_pause)
            self.btn_open.show()
            self.btn_close.show()
        else:
            self.btn_open.hide()
            self.btn_close.hide()
        self.btn_pause.setFlat(self.current != 2)
        if self.current == 0:
            self.btn_close.setStyleSheet("background-color: 'red';")
            self.btn_open.setFlat(True)
        elif self.current == 1:
            self.btn_close.setStyleSheet("background-color: 'green';")
            self.btn_open.setFlat(False)
            

        return r
    