#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
from PyQt4 import QtGui, QtCore
import functools
from .. import parameters as params
import os

def add_button(parent, layout, icon_path, text, size, row, column, rowspan=1, columnspan=1):
    button = QtGui.QToolButton(parent)
    button.setIcon(QtGui.QIcon(icon_path))
    button.setText(text)
    button.setIconSize(QtCore.QSize(size, size))
    button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
    layout.addWidget(button, row, column, rowspan, columnspan, QtCore.Qt.AlignTop)
    return button

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
            if title.lower() == 'kiln' and server._writeLevel < 4:
                continue
            instrument_enabled_option = 'eq_' + name
            if server.has_key(instrument_enabled_option):
                instrument_enabled = server[instrument_enabled_option]
                if not instrument_enabled:
                    logging.debug('Instrument ' + name + ' disabled')
                    continue
            else:
                logging.debug('Ignoring unknown instrument', title, name)
                continue
            obj = getattr(server, name, False)
            if obj is False:
                logging.debug('%s %s', 'Instrument not found', name)
                continue
            f = functools.partial(self.setInstrument, obj, preset=name)
            self.func.append(f)
            current_instrument_layout = QtGui.QGridLayout()
            self.lay.addLayout(current_instrument_layout)

            button = add_button(self,
                                current_instrument_layout,
                                os.path.join(params.pathArt, title + '.svg'),
                                title,
                                200,
                                0,
                                0,
                                1,
                                -1)
            self.connect(button, QtCore.SIGNAL('pressed()'), f)

            presets = filter(lambda preset: preset not in ['default', 'factory_default'],
                             obj.listPresets())
            for current_column, preset in enumerate(presets):
                button = add_button(self,
                                    current_instrument_layout,
                                    os.path.join(params.pathArt,
                                                 preset.split('_')[-1] + '.png'),
                                    ' '.join(preset.split('_')[:-1]),
                                    50,
                                    1,
                                    current_column)

                f = functools.partial(self.setInstrument, preset=preset, remote=obj)
                self.connect(button, QtCore.SIGNAL('pressed()'), f)
