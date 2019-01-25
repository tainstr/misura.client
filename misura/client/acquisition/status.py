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
        h1 = fp+handle
        pos = confdb.rule_opt_status(h1)
        # Skip if not included
        if not pos:
            continue
        # Skip if hidden
        if confdb.rule_opt_hide(h1):
            continue
        pos, force = pos
        if pos:
            if h1 in opts['kid']:
                continue
            opts['kid'].add(h1)
            while pos in opts:
                pos += 0.01
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
        opts = {'kid': set()} # position: (parent, handle)
        opts = add_object_options(server, opts)
        opts = add_object_options(remObj.measure, opts)
        Nsamples = remObj.measure['nSamples']
        for i in xrange(Nsamples + 1):
            name = 'sample' + str(i)
            if not remObj.has_child(name):
                continue
            smp = getattr(remObj, name)
            opts = add_object_options(smp, opts)
        
        for row in confdb['opt_status'][1:]:
            if not row[0].startswith('^/'):
                continue
            rule=row[0].replace('^/', '').replace('$','').split('/')
            obj = server
            while len(rule)>1 and rule[0].isalnum():
                # Child object name
                try:
                    obj = obj.child(rule.pop(0))
                    if ('initTest' in obj) and obj['fullpath']!=remObj['fullpath'] and obj['devpath']!='kiln':
                        logging.debug('Skip foreign instrument', obj['fullpath'], row[0])
                        obj = None
                except:
                    obj = None
                if not obj:
                    break
                
            # If object was found
            if obj:
                try:
                    opts = add_object_options(obj, opts)
                except:
                    pass
            
        done_motor = False
        positions = sorted(opts.keys())
        positions.remove('kid')
        for pos in positions:
            # Inject motor after third position
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
            if Nsamples>1 and parent['devpath'].startswith('sample') and 'ii' in parent:
                lbl = wg.label_widget
                lbl.setText(lbl.text()+' ({})'.format(parent['idx']))
            
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
