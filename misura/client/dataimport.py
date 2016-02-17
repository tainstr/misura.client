# -*- coding: utf-8 -*-
"""Utilities for importing data into Misura HDF file format"""

from misura.canon.option import ao
from misura.canon.logger import Log as logging

def base_dict():
    base_dict = {}
    ao(base_dict, 'name', 'String', 'Name', name='Name')
    ao(base_dict, 'mro', 'List', name='mro', attr=['Hidden'])
    ao(base_dict, 'comment', 'String', '')
    ao(base_dict, 'dev', 'String', attr=['Hidden'])
    ao(base_dict, 'devpath', 'String', attr=['Hidden'])
    ao(base_dict, 'fullpath', 'String', attr=['Hidden'])
    ao(base_dict, 'zerotime', 'Float', name='Start time', attr=['Hidden'])
    ao(base_dict, 'initInstrument', 'Progress', attr=['Hidden'])
    return base_dict

def measure_dict():
    measure_dict = base_dict()
    measure_dict['name']['current'] = 'Measure'
    ao(measure_dict, 'nSamples', 'Integer', 1, attr=['Hidden'])
    ao(measure_dict, 'id', 'String', 'Conversion source ID')
    ao(measure_dict, 'uid', 'String', 'Unique ID')
    ao(measure_dict, 'date', 'Date', '00:00:00 01/01/2000', name='Test date')
    ao(measure_dict, 'elapsed', 'Float', name='Test duration', unit='second')
    ao(measure_dict, 'operator', 'String', 'Operator')
    return measure_dict

def smp_dict():
    smp_dict = base_dict()
    smp_dict['name']['current'] = 'Sample'
    ao(smp_dict, 'idx', 'Integer', attr=['Hidden'])
    ao(smp_dict, 'ii', 'Integer', attr=['Hidden'])
    ao(smp_dict, 'initialDimension', 'Float', 0., name='Initial Dimension')
    return smp_dict
    
def kiln_dict():
    kiln_dict = base_dict()
    kiln_dict['name']['current'] = 'Kiln'
    ao(kiln_dict, 'serial', 'String')
    ao(kiln_dict, 'curve', 'Hidden', [[0, 0]], 'Heating curve')
    ao(kiln_dict, 'thermalCycle', 'ThermalCycle', 'default')
    ao(kiln_dict, 'T', 'Float', 0, 'Temperature', unit='celsius')
    ao(kiln_dict, 'P', 'Float', 0, 'Power', unit='percent')
    ao(kiln_dict, 'S', 'Float', 0, 'Setpoint', unit='celsius')
    ao(kiln_dict, 'maxHeatingRate', 'Float', 0, 'Max Heating Rate')
    ao(kiln_dict, 'maxControlTemp', 'Float', 0, 'Max Control Temp')
    ao(kiln_dict, 'minControlTemp', 'Float', 0, 'Min Control Temp')
    ao(kiln_dict, 'maxElementTemp', 'Float', 0, 'Max Element Temp')
    ao(kiln_dict, 'minElementTemp', 'Float', 0, 'Min Element Temp')
    return kiln_dict

def instr_dict():
    instr_dict = base_dict()
    ao(instr_dict, 'nSamples', 'Integer', 1, attr=['Hidden'])
    ao(instr_dict, 'camera', 'Role', ['camerapath', 'default'])
    ao(instr_dict, 'devices', 'List', attr=['Hidden'])
    ao(instr_dict, 'initTest', 'Progress', attr=['Hidden'])
    ao(instr_dict, 'closingTest', 'Progress', attr=['Hidden'])
    return instr_dict

def server_dict():
    server_dict = base_dict()
    server_dict['name']['current'] = 'server'
    ao(server_dict, 'name', 'String', 'server')
    ao(server_dict, 'isRunning', 'Boolean', False)
    ao(server_dict, 'runningInstrument', 'String')
    ao(server_dict, 'lastInstrument', 'String')
    ao(server_dict, 'log', 'Log')
    return server_dict


def smp_tree():
    """Tree for generical sample"""
    return  {'self': smp_dict()}

def instr_tree(): 
    """Tree for generical instrument"""
    return {'self': instr_dict(),
                'measure': {'self': measure_dict()}}

def tree_dict(): 
    """Main tree"""
    return {'self': server_dict(),
            'kiln': {'self': kiln_dict()}}


def create_tree(outFile, tree, path='/'):
    """Recursive tree structure creation"""
    for key, foo in tree.list():
        if outFile.has_node(path, key):
            logging.debug('Path already found:', path, key)
            continue
        logging.debug('%s %s %s', 'Creating group:', path, key)
        outFile.create_group(path, key, key)
        dest = path + key + '/'
        if outFile.has_node(dest):
            continue
        create_tree(outFile, tree.child(key), dest)
