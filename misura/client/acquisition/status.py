#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from .. import widgets
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

class Status(QtGui.QWidget):

    def __init__(self, server, remObj, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.widgets = {}
        # TODO: accept drops
        self.lay = QtGui.QFormLayout()
        self.lay.setLabelAlignment(QtCore.Qt.AlignRight)
        self.lay.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)
        wg = widgets.build(server, server, server.gete('isRunning'))
        self.insert_widget(wg)
        has_kiln = server.has_child('kiln')
        if has_kiln:
            wg = widgets.build(server, server.kiln, server.kiln.gete('analysis'))
            self.insert_widget(wg)
        for opt in 'name', 'elapsed':
            wg = widgets.build(
                server, remObj.measure, remObj.measure.gete(opt))
            self.insert_widget(wg)
        if has_kiln:
            if server.kiln['motorStatus'] >= 0:
                wg = widgets.build(
                    server, server.kiln, server.kiln.gete('motorStatus'))
                wg.force_update = True
                self.insert_widget(wg)
            for opt in 'T', 'S', 'P', 'Ts', 'Tk', 'Th', 'Te':
                # Skip empty IO pointers
                opt_dict = server.kiln.gete(opt)
                if opt_dict.has_key('options') and opt_dict['options'][0] == 'None':
                    continue
                wg = widgets.build(server, server.kiln, opt_dict)
                if wg.type.endswith('IO'):
                    wg.value.force_update = True
                else:
                    wg.force_update = True
                self.insert_widget(wg)
        n = remObj['devpath']

        if n != 'kiln':
            if n == 'hsm':
                self.add_samples_option(server, remObj, 'h')
            elif n in ('vertical', 'horizontal', 'flex'):
                self.add_samples_option(server, remObj, 'd')
                self.add_samples_option(server, remObj, 'initialDimension')
            elif n=='dta':
                self.add_samples_option(server, remObj, 'deltaT')

        self.setLayout(self.lay)

    def add_samples_option(self, server, remObj, option):
        for i in range(remObj.measure['nSamples'] + 1):
            name = 'sample' + str(i)
            if not remObj.has_child(name):
                continue
            smp = getattr(remObj, name)
            print 'Building widget', smp['fullpath'], option
            wg = widgets.build(server, smp, smp.gete(option))
            self.insert_widget(wg)

    def insert_widget(self, wg):
        if wg is False:
            logging.debug("Cannot insert widget", wg)
            return False
        self.widgets[wg.prop['kid']] = wg
        self.lay.addRow(wg.label_widget, wg)
        return True

    def showEvent(self, event):
        for kid, wg in self.widgets.iteritems():
            if not wg.force_update:
                wg.soft_get()
        return super(Status, self).showEvent(event)
