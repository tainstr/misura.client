#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from .. import widgets
from ..clientconf import confdb
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

def add_object_options(remObj, opts):
    fp = remObj['fullpath']
    for handle in remObj.keys():
        pos = confdb.rule_opt_status(fp+handle)
        if not pos:
            continue
        pos, force = pos
        if pos:
            opts[pos] = (remObj, handle, force)
    return opts
            

class Status(QtGui.QWidget):

    def __init__(self, server, remObj, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.widgets = {}
        # TODO: accept drops
        self.lay = QtGui.QFormLayout()
        self.lay.setLabelAlignment(QtCore.Qt.AlignRight)
        self.lay.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)
        
        # Collect available ordered options
        opts = {} # position: (parent, handle)
        opts = add_object_options(server, opts)
        opts = add_object_options(server.kiln, opts)
        opts = add_object_options(remObj.measure, opts)
        for i in range(remObj.measure['nSamples'] + 1):
            name = 'sample' + str(i)
            if not remObj.has_child(name):
                continue
            smp = getattr(remObj, name)
            opts = add_object_options(smp, opts)
        
        done_motor = False
        positions = sorted(opts.keys())
        for pos in positions:
            if pos>3 and not done_motor:
                self.add_motorStatus(server)
                done_motor = True
            parent, handle, force = opts[pos]
            # Skip empty IO pointers
            opt = parent.gete(handle)
            if opt.has_key('options') and opt['options'][0] == 'None':
                    continue
            wg = widgets.build(server, parent, opt)
            if wg.type.endswith('IO'):
                wg.value.force_update = force
            else:
                wg.force_update = force
            
            self.insert_widget(wg)
        


        self.setLayout(self.lay)
        
    def add_motorStatus(self, server):
        if server.has_child('kiln'):
            if server.kiln['motorStatus'] >= 0:
                wg = widgets.build(
                    server, server.kiln, server.kiln.gete('motorStatus'))
                wg.force_update = True
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
