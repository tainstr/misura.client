#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Save/restore full instrument configuration using single INI file. """
try:
    import configparser
except:
    import ConfigParser as configparser
import ast
import os

from .live import registry
from .widgets import RunMethod

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
        if not tosave(entry, ['ReadOnly', 'Button']):
            continue
        for key, val in entry.iteritems():
            if key in ('name', 'handle', 'type', 'factory_default', 'kid'):
                continue
            val = repr(val)
            logging.debug('Setting: ', preset, fp+k+'.'+key , val)
            conf.set(cpreset, fp+k+'.'+key , val)
        

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
    
def rescan_enumerated(conf, srv):
    # Enumerated options
    done = 0
    for key in ('tacontrollers', 'epack'):
        kkey = '/smaug/{}.current'.format(key)
        if not conf.has_option('default', kkey):
            continue
        val = conf.get('__default__', kkey)
        logging.debug('Setting enumerated option', kkey, val)
        srv.smaug[key] = val
        done += 1
    if done:
        r = srv.smaug.rescan()
        logging.debug('Rescan', r)
        
    
def restore(srv, file_path='ini.ini', serials=None, override=[], jobs=lambda *a: 1, 
            job=lambda *a: 1,
            done=lambda *a: 1):
    serials = serials or []
    ini = open(file_path, 'r').read()
    for (old,new) in serials:
        ini = ini.replace(old, new)
    f1 = file_path+'.tmp'
    open(f1, 'w').write(ini)
    conf = configparser.SafeConfigParser()
    conf.optionxform = str
    conf.read(f1)
    
    for sec, key, val in override:
        conf.set(sec, key, repr(val))
        
    rescan_enumerated(conf, srv)
        
    jname = 'Import configuration from \n'+str(f1)  
    print conf._sections.values()[0]
    tot = sum(map(lambda sec: len(sec.keys()), conf._sections.values()))
    jobs(tot, jname)
    

        
    i = 0
    for sec in conf.sections():
        if sec==metasection:
            continue
        msec = sec
        if sec=='__default__':
            msec = 'default'
        for opt in conf.options(sec):
            job(i, jname)
            i+=1
            val = conf.get(sec, opt)
            val = ast.literal_eval(val)
            opt, key = opt.split('.')
            fp = opt.split('/')
            opt = fp.pop(-1)
            fp = '/'.join(fp)
            logging.debug('Setting', fp, opt, key, 'to', val)
            
            obj = srv.toPath(fp)
            if obj is None:
                logging.error('Target object does not exist:', fp)
                continue
            
            if msec not in obj.listPresets():
                obj.save(msec)
            obj.set_to_preset(opt, msec, val, key)
            
    done(jname)
            
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
    c.addItem('None', '')
    return c

def morla_serial(s):
    if s.startswith('/morla/'):
        return s[7:]
    return s
    
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
            elif not found:
                c.setCurrentIndex(len(self.new_serials))
                
        
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
        
        r = self.layout().rowCount()+1
        serial = '' 
        if conf.has_option('__default__', '/eq_sn.current'):
            serial = '({})'.format(ast.literal_eval(conf.get('__default__', '/eq_sn.current')))
        lbl = QtGui.QLabel(_('Serial: {}'.format(serial)))
        lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.layout().addWidget(lbl, r, 0)
        self.instrument_serial_number = QtGui.QLineEdit(self.srv['eq_sn'])
        self.layout().addWidget(self.instrument_serial_number, r, 1)

        r = self.layout().rowCount()+1
        serial = '' 
        if conf.has_option('__default__', '/kiln/ksn.current'):
            serial = '({})'.format(ast.literal_eval(conf.get('__default__', '/kiln/ksn.current')))
        lbl = QtGui.QLabel(_('Kiln Serial: {}'.format(serial)))
        lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.layout().addWidget(lbl, r, 0)
        self.kiln_serial_number = QtGui.QLineEdit(self.srv.kiln['ksn'])
        self.layout().addWidget(self.kiln_serial_number, r, 1)
           
        self.btn_apply = QtGui.QPushButton(_('Apply'))
        self.btn_apply.clicked.connect(self.apply)
        self.layout().addWidget(self.btn_apply, self.layout().rowCount()+1, 1) 
        
        self.exec_()
        
    def apply(self):
        logging.debug('APPLY')
        self.srv['eq_sn'] = self.instrument_serial_number.text()
        self.srv.kiln['ksn'] = self.kiln_serial_number.text()
        override =[('__default__', '/eq_sn.current', self.srv['eq_sn']),
                   ('__default__', '/kiln/ksn.current', self.srv.kiln['ksn'])]
        serials = []
        for i, c in enumerate(self.combos):
            c = self.combos[i]
            new_serial = str(c.itemData(c.currentIndex()))
            if not new_serial:
                continue
            old_serial = self.old_serials[i][2]
            logging.debug('new_serial', self.old_serials[i][0], new_serial)
            serials.append((old_serial, new_serial))
            if new_serial.startswith('/morla/'):
                serials.append((morla_serial(old_serial),
                                morla_serial(new_serial)))
        logging.debug('SERIALS', serials)
        
        r = RunMethod(restore, self.srv, self.filename, serials, override,
                registry.tasks.jobs, registry.tasks.job, registry.tasks.done)
        r.pid = 'Import configuration'
        r.do()
        self.done(0)
        
            