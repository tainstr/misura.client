#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore
import functools
from .. import parameters as params


class InstrumentSelector(QtGui.QWidget):

    def __init__(self, parent, setInstrument):
        QtGui.QWidget.__init__(self, parent)
        self.lay = QtGui.QHBoxLayout(self)
        self.setLayout(self.lay)
        self.setInstrument = setInstrument
        self.redraw()

    def redraw(self):
        while True:
            item = self.lay.takeAt(0)
            if item in [0, None]:
                break
        self.func = []
        server = self.parent().server
        inlist = []
        if server.has_key('instruments'):
            inlist = server['instruments']
        for (title, name) in inlist:
            opt = 'eq_' + name
            if server.has_key(opt):
                if not server[opt]:
                    logging.debug('%s %s', opt, server[opt])
                    continue
            elif params.debug:
                logging.debug(
                    '%s %s %s', 'Enabling unknown instrument...', title, name)
            else:
                logging.debug(
                    '%s %s %s', 'Ignoring unknown instrument', title, name)
                continue
            obj = getattr(server, name, False)
            if obj is False:
                logging.debug('%s %s', 'Instrument not found', name)
                continue
            f = functools.partial(self.setInstrument, obj)
            self.func.append(f)
            button = QtGui.QPushButton(title, self)
            self.lay.addWidget(button)
            self.connect(button, QtCore.SIGNAL('pressed()'), f)
