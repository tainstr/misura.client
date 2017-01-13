#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
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
        self.redraw(reget=False)
        self.lay.addWidget(self.combo)
        self.connect(
            self.combo,  QtCore.SIGNAL('currentIndexChanged(int)'), self.try_set)

    def enterEvent(self, event):
        """Update the widget anytime the mouse enters its area.
        This must be overridden in one-shot widgets, like buttons."""
        if self.type == 'FileList':
            self.redraw()
        else:
            self.get()
        return ActiveWidget.enterEvent(self, event)
    
    def try_set(self, idx):
        result = self.set(idx)
        new_idx = self.adapt2gui(result)
        if new_idx!=idx:
            self.redraw()

    def redraw(self, reget=True):
        self.combo.blockSignals(True)
        # Cleans combo entries
        self.combo.clear()
        # Get new property
        self.prop = self.remObj.gete(self.handle)
        logging.debug('%s %s', 'aChooser.redraw', self.prop)
        opt = self.prop.get('options', [])
        vals = self.prop.get('values', opt)
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
        # Restore signals
        self.combo.blockSignals(False)

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
            logging.debug('Not setting',self.handle, repr(val))
            return True

        QtCore.QTimer.singleShot(0, lambda: self.remObj.set(self.handle, val))
        return self.get()
