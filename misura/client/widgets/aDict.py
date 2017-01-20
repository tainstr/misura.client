#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from .. import _
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from misura.client import units


class aDict(ActiveWidget):

    def __init__(self, server, path, prop, parent=None):
        ActiveWidget.__init__(self, server, path, prop, parent)
        self.map = {}
        self.cmap = {}
        # Cause update immediately after initialization
        self.emit(QtCore.SIGNAL('selfchanged()'))

    def adapt2srv(self, val):

        rmap = {}
        for key, spinbox in self.map.iteritems():
            rmap[key] = spinbox.value()
        for key, textbox in self.cmap.iteritems():
            rmap[key] = textbox.text()
        # Do unit conversion
        for key, val in rmap.copy().iteritems():
            val = units.Converter.convert(self.prop['unit'][key], None, val)
            # Time correction
            if key == 'time' and 'Duration' not in self.handle:
                if val > self.server['zerotime']:
                    val += self.server['zerotime']
            rmap[key] = val
        return rmap

    def adapt2gui(self, vdict):
        # Do unit conversion
        for key, val in vdict.copy().iteritems():
            # Time correction
            if key == 'time' and val != 'None' and 'Duration' not in self.handle:
                if val > self.server['zerotime']:
                    val -= self.server['zerotime']
            val = units.Converter.convert(self.prop['unit'][key], None, val)
            vdict[key] = val
        return vdict

    def update(self):
        self.clear()
        self.map = {}
        self.cmap = {}
        if self.current is None:
            logging.debug('No current value to update', self.label)
            return
        cur = self.adapt2gui(self.current)
        for key, val in cur.iteritems():
            if type(val) == type(''):
                sb = QtGui.QLineEdit(val)
                if not self.readonly:
                    self.connect(
                        sb, QtCore.SIGNAL('textEdited(QString)'), self.set)
                self.cmap[key] = sb
                self.lay.addWidget(QtGui.QLabel(key.capitalize() + ':'))
                self.lay.addWidget(sb)
            else:
                sb = QtGui.QDoubleSpinBox()
                sb.setPrefix(key.capitalize() + ': ')
                min = MIN
                max = MAX
                if self.prop.has_key('min'):
                    min = self.prop['min'][key]
                if self.prop.has_key('max'):
                    max = self.prop['max'][key]
                sb.setRange(min, max)
                sb.setSingleStep(1)
                logging.debug('updating', self.label, val)
                sb.setValue(val)
                if not self.readonly:
                    self.connect(
                        sb, QtCore.SIGNAL('valueChanged(double)'), self.set)
                self.map[key] = sb
                self.lay.addWidget(sb)
