#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Save/restore full instrument configuration using single INI file. """
try:
    import configparser
except:
    import ConfigParser as configparser
import ast
import os

from PyQt4 import QtGui, QtCore, uic

from misura.canon.logger import get_module_logging
from misura.canon.option import tosave
logging = get_module_logging(__name__)

from . import _

def dump_preset(obj, keys, fp, preset, conf):
    cpreset = preset
    if preset=='default':
        cpreset='__default__'
    if not conf.has_section(cpreset):
        conf.add_section(cpreset)
    for k in keys:
        entry = obj.get_from_preset(k, preset, True)
        if entry is None:
            continue
        entry = entry['_entry']
        if not tosave(entry):
            continue
        val = repr(entry['current'])
        logging.debug('Setting: ', preset, fp+k , val, val)
        conf.set(cpreset, fp+k , val)
        

def parse_obj(obj, conf):
    fp = obj['fullpath']
    logging.debug('Saving object', fp)
    keys = obj.keys()
    presets = obj.listPresets()
    for preset in presets:
        if preset=='factory_default':
            logging.debug('Skipping factory default')
            continue
        dump_preset(obj, keys, fp, preset, conf)
    # Iterative call
    for sub in obj.devices:
        parse_obj(sub, conf)

_lsd = lambda obj: [(d['devpath'],d['name'], d['fullpath']) for d in obj.devices] 

def list_serialized_devices(srv):
    g =  _lsd(srv.beholder) + _lsd(srv.morla) + _lsd(srv.smaug)
    return g
    
metasection = '***METASECTION***'
def save(srv, file_path='ini.ini'):
    conf = configparser.SafeConfigParser()
    conf.optionxform = str
    parse_obj(srv, conf)
    conf.add_section(metasection)
    g = list_serialized_devices(srv)
    conf.set(metasection, 'serials', repr(g))
    conf.write(open(file_path, 'w'))
    
def restore(srv, file_path='ini.ini', serials=None):
    serials = serials or []
    ini = open(file_path, 'r').read()
    for (old,new) in serials:
        ini = ini.replace(old, new)
    f1 = file_path+'.tmp'
    open(f1, 'w').write(ini)
    conf = configparser.SafeConfigParser()
    conf.optionxform = str
    conf.read(f1)
    for sec in conf.sections():
        if sec==metasection:
            continue
        msec = sec
        if sec=='__default__':
            msec = 'default'
        for opt in conf.options(sec):
            val = conf.get(sec, opt)
            val = ast.literal_eval(val)
            fp = opt.split('/')
            opt = fp.pop(-1)
            fp = '/'.join(fp)
            logging.debug('Setting', fp, opt,'to', val)
            
            obj = srv.toPath(fp)
            if obj is None:
                logging.error('Target object does not exist:', fp)
                continue
            
            if msec not in obj.listPresets():
                obj.save(msec)
            obj.set_to_preset(opt, msec, val)
    #os.remove(f1)
            
def export_configuration(srv, parent=None):
    filename = QtGui.QFileDialog.getSaveFileName(parent, 
                                                     _('Choose a file name where to export to'), 
                                                     '', 'INI (*.ini *.INI)')
    if not filename:
        logging.debug('Configuration Export Aborted')
        return False
    if not filename.lower().endswith('ini'):
        filename+='.ini'
    logging.debug('Exporting configuration to', filename)
    save(srv, filename)
    QtGui.QMessageBox.information(parent, 
                                  _('Export was successful'),
                                  _('Exported configuration to:\n')+filename)

def import_configuration(srv, parent=None):
    filename = QtGui.QFileDialog.getOpenFileName(parent, 
                                                     _('Choose an INI file to import from'), 
                                                     filter='INI (*.ini *.INI)')
    if not filename:
        logging.debug('Configuration Import Aborted')
        return False
    logging.debug('Importing configuration from', filename)
    snr = SerialNumberReplacer(filename, srv, parent)
    snr.do()
    
def make_combo(serials):
    c = QtGui.QComboBox()
    for (serial, name, fp) in serials:
        lbl = 'Name: {}, {}'.format(name, fp)
        c.addItem(lbl, fp)
    return c
    
class SerialNumberReplacer(QtGui.QDialog):
    def __init__(self, filename, srv, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        self.setWindowTitle('Device roles checkup')
        self.filename = filename
        self.srv = srv
        
        lay = QtGui.QGridLayout()
        self.setLayout(lay)
            
    def add_serial_selector(self, serial, name, fp):
        old = 'Name: {}, {}'.format(name, fp)
        r = self.layout().rowCount()+1
        self.layout().addWidget(QtGui.QLabel(old), r, 0)
        c = make_combo(self.new_serials)
        self.layout().addWidget(c, r, 1)
        self.combos.append(c)
        
        # Search a matching serial
        found = 0
        for i, (new_serial, new_name, new_fp) in enumerate(self.new_serials):
            if new_fp == fp:
                c.setCurrentIndex(i)
                break
            if new_serial == serial:
                c.setCurrentIndex(i)
                found = 1
            if new_name == name and not found:
                c.setCurrentIndex(i)
                
        
    def do(self):
        conf = configparser.SafeConfigParser()
        conf.optionxform = str
        conf.read(self.filename)
        
        self.old_serials = ast.literal_eval(conf.get(metasection, 'serials'))
        
        if not self.old_serials:
            logging.debug('No serials to be replaced!')
            self.apply()
            return False
        logging.debug('SerialNumberReplacer init', self.filename, self.old_serials)
        self.new_serials = list_serialized_devices(self.srv)
        self.combos = []
        for (serial, name, fp) in self.old_serials:
            self.add_serial_selector(serial, name, fp)
           
        self.btn_apply = QtGui.QPushButton(_('Apply'))
        self.btn_apply.clicked.connect(self.apply)
        self.layout().addWidget(self.btn_apply, self.layout().rowCount()+1, 1) 
        
        self.exec_()
        
    def apply(self):
        logging.debug('APPLY')
        serials = []
        for i, c in enumerate(self.combos):
            c = self.combos[i]
            new_serial = c.itemData(c.currentIndex())
            logging.debug('new_serial', self.old_serials[i][0], new_serial)
            serials.append((self.old_serials[i][2],
                            str(new_serial)))
        logging.debug('SERIALS', serials)
        restore(self.srv, self.filename, serials)
        self.done(0)
        
            