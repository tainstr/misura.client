#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from misura.client.widgets.active import *
from misura.client import units
from aDict import aDict


class aMeta(ActiveWidget):

    def __init__(self, server, path, prop, parent=None):
        ActiveWidget.__init__(self, server, path, prop, parent)
        self.lbl = QtGui.QPushButton('...')
        self.lbl.setFlat(True)
        self.lay.addWidget(self.lbl)
        self.map = {}
        self.cmap = {}
        # Cause update immediately after initialization
        self.emit(QtCore.SIGNAL('selfchanged()'))
        self.connect(self.lbl, QtCore.SIGNAL('clicked()'), self.edit)
        self.setAcceptDrops(True)
        self.label_widget.setAcceptDrops(True)
        self.lbl.setAcceptDrops(True)
        self.set_enabled()

    def update(self):
        msg = ''
        for key in ['temp', 'time']:
            val = self.current[key]
            if val == 'None':
                msg = 'Empty\n'
                break
            if key == 'time' and 'Duration' not in self.handle:
                # Make relative, if absolute
                if val > self.server['zerotime']:
                    val -= self.server['zerotime']
            msg += '{}: {:.1f}\n'.format(key.capitalize(), val)

        if len(msg):
            msg = msg[:-1]
            self.lbl.setText(msg)

    def edit(self):
        editor = aDict(self.server, self.remObj, self.prop)
        dia = QtGui.QDialog()
        lay = QtGui.QVBoxLayout()
        lay.addWidget(editor.label_widget)
        lay.addWidget(editor)
        dia.setLayout(lay)
        dia.setWindowTitle('Edit metadata: {}'.format(self.prop['name']))
        dia.exec_()

    def receive_drop(self, event):
        """Receive drops from MiniImage"""
        txt = str(event.mimeData().text())
        logging.debug('Received drop event', txt)
        if not txt.startswith('point:'):
            return
        foo, path, t, T = txt.split(':')
        if not self.prop['kid'].startswith(path):
            logging.debug("Wrong destination", path)
        self.current['time'] = float(t)
        self.current['temp'] = float(T)
        self.current['value'] = 'None'
        self.set(self.current)
        self.update()
