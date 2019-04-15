#!/usr/bin/python
# -*- coding: utf-8 -*-
"""FlashLine directory structure parser"""
import numpy as np
import xml.parsers.expat as expat
import os
import collections
import hashlib
import re


from misura.canon.csutil import decode_datetime
from misura.canon.logger import get_module_logging
from traceback import format_exc
logging = get_module_logging(__name__)


from .debug_table import debug_table
from . import results
from . import cdv



header_fields = ['format',
                 'format_version',
                 'channel',
                 'datetime',
                 'test',
                 'sample',
                 'sample_folder',
                 'setpoint_temperature',
                 'counter',
                 'test_counter',
                 'geometry',
                 'instrument',
                 'operator',
                 'weight',
                 '_',
                 'software_version'] + ['_'] * 23 + [
    'serial'] + ['_'] * 3 + [
    'board_serial',
    '_',
    'carousel',
    'points',
    'board',
    '_', '_']


def decode_data(data, factor=3276.8):
    # Skip first 2 points and divide by factor
    data = np.fromstring(data, np.int16)[2:] / factor
    return data

extract_number = lambda chars: "".join(_ for _ in chars if _ in "-.1234567890")


def _decode_setpoint_temperature(val):
    foo, setpoint, temperature = val.split(':')
    return float(extract_number(setpoint)), float(extract_number(temperature))


def decode_header(header):
    """Further parses important header values"""
    setpoint, temperature = _decode_setpoint_temperature(
        header['setpoint_temperature'])
    header['setpoint'] = setpoint
    header['temperature'] = temperature
    # New header definition
    fmt = '%a %b %d %H:%M:%S %Y'
    # Old header definition
    if '-' in header['datetime']:
        fmt = '%Y-%m-%d %H:%M:%S'
    header['datetime'] = decode_datetime(
        header['datetime'], format=fmt)
    del header['_']
    return header

def acquisition_rate(filename):
    """Parses .rat files for acquisition rate information"""
    rate, channels = 30000., 2
    if not os.path.exists(filename):
        logging.error('No rate file found, assuming standard rate:', filename)
        return rate, channels
    n = 0
    channels = 0
    for n,line in enumerate(open(filename, 'r').readlines()):
        line = line[:-2]
        if n == 0:
            rate = float(line)
        elif n == 1:
            channels = int(line[0])
        else:
            break
    if not channels:
        logging.error('Unable to parse number of channels')
        channels = 2
    return rate, channels

def channel_header(filename):
    header = {'_import_filename': filename}
    header['_'] = {}    
    channel_file = open(filename, 'rb')
    # Read first 50 lines of header and put the rest in data
    n = 0
    for line in channel_file.readlines():
        n += 1
        if n >= 51:
            break
        line = str(line[:-1])
        field = header_fields[n - 1]
        if field == '_':
            header[field][n] = line
        else:
            header[field] = line
    channel_file.close()
    result = decode_header(header)
    rate, channels = acquisition_rate(filename[:-3]+'rat')
    result['frequency'] = rate/channels
    return result

def channel_data(filename):
    """Reads a channel file (.fw0,1,)"""
    data = []
    channel_file = open(filename, 'rb')
    # Read first 50 lines of header and put the rest in data
    n = 0
    for line in channel_file.readlines():
        n += 1
        if n <= 50:
            continue
        data.append(line)
    channel_file.close()
    # Rebuild data from remaining lines (should be only one)
    data = ''.join(data)
    return decode_data(data)

def channel(filename):
    return channel_data(filename), channel_header(filename)

class AutoDictionary(collections.defaultdict):
    def __init__(self, *a, **k):
        super(self.__class__, self).__init__(self.__class__)
        self['__data__'] = []
    
# XML Parsing
from xml.sax.saxutils import escape, unescape

def escape_specials(dat):
    todo = ('>', '&gt;'), ('<','&lt;'), ('"', '&quot;'), ('&','&amp;'), ("'", '&apos;')
    esc = '$$##$$--$$'
    # Protect
    found = re.findall('&(.+?);', dat)
    for protect in found:
        dat = dat.replace(protect, esc+protect[1:])
    # Replace
    dat = escape(dat)
    # Deprotect
    for protect in found:
        dat = dat.replace(esc+protect[1:], protect)
    return dat
    
    
class XmlDictionaryParser(object):

    def __init__(self):
        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.start
        self.parser.EndElementHandler = self.end
        self.parser.CharacterDataHandler = self.data
        self.info= collections.defaultdict(AutoDictionary)
        self.key = []

    def read_file(self, filename):
        dat = open(filename, 'r').read()
        for tag in ('TestTitle', 'SampleTitle', 'SampleFileID', 'TestID',
            'FurnaceTitle', 'FurnaceDescription', 'Operator'):
            targets = re.findall("\<{0}\>(.+?)\</{0}\>".format(tag), dat)
            dat0 = dat
            for target in targets:
                esc = escape_specials(target)
                if esc!=target:
                    logging.debug('Fixed xml escaping',esc, target)
                dat = dat.replace(target, esc)
            

  
        self.parser.Parse(dat, 0)

    def __del__(self):
        self.parser.Parse("", 1)
        del self.parser

    def get_key(self):
        """Resolve current key"""
        d = self.info
        n = 0
        for k in self.key:
            d = d[k]
        return d

    def start(self, name, attrs):
        self.key.append(name)

    def end(self, data):
        self.key.pop(-1)

    def data(self, data):
        data = unescape(data)
        d = self.get_key()
        d['__data__'].append(data)

def get_data(info, paths, index=0, alternative=None):
    obj = info
    paths.append('__data__')
    for path in paths:
        if not path in obj:
            logging.error('Cannot find TestInformation.xml property', path, alternative)
            return alternative
        obj = obj[path]
    if len(obj)-1<index:
        logging.error('Cannot find TestInformation.xml property', paths, alternative)
        return alternative
    return obj[index]
        
        
def parameters(filename):
    xmlparser = XmlDictionaryParser()
    xmlparser.read_file(filename)
    info = xmlparser.info['TestInformation']
    dname = os.path.basename(os.path.dirname(filename))
    uid = get_data(info, ['TestTitle'],0,dname) + get_data(info, ['UniqueName'],0,'')
    info['uid'] = hashlib.md5(uid).hexdigest()
    info['basedir'] = os.path.dirname(filename)
    return info

def decode_name(name):
    segment = int(name[:3]) - 1
    if segment < 0: segment = 0
    sample = int(name[3:5]) - 1
    if sample < 0: sample = 0
    shot = int(name[5:8]) - 1
    return sample, segment, shot

def sample_folder(path):
    """Discovers all shots contained in a sample directory and parses them in.
    shots={segment: {shot: {header:..., fw0:..., fw1:...}}}"""
    shots = collections.defaultdict(lambda: collections.defaultdict(dict))
    segments = {}
    if not os.path.exists(path):
        return {}, {}, []
    for name in os.listdir(path):
        vname = name.split('.')
        if len(vname)>2 or not (vname[-1] in ['fw0', 'fw1'] and len(name) == 12):
            continue
        base, ext = vname 
        sample, segment, shot = decode_name(name)
        fw = os.path.join(path, name)
        
        try:
            header = channel_header(fw)
        except:
            logging.error('Fatal error importing channel', fw)
            continue
        try:
            if not shots[segment][shot].has_key('cdv'):
                shots[segment][shot]['cdv'] = cdv.CDV.open(os.path.join(path, base+'.cdv'))
        except:
            logging.warning('Error importing shot cdv: ',fw,format_exc())
            shots[segment][shot]['cdv'] = None
        try:
            if not shots[segment][shot].has_key('cdt'):
                shots[segment][shot]['cdt'] = cdv.GenericKeyValueResultFile.open(os.path.join(path, base+'.cdt'))
        except:
            logging.warning('Error importing shot cdt: ',fw,format_exc())
            shots[segment][shot]['cdt'] = None
            #continue
        segments[segment] = header['setpoint']
        shots[segment][shot][ext] = header
        shots[segment][shot]['header'] = header
        
    results_table = results.all_table(os.path.join(path, 'results.all'))
    return segments, shots, results_table
    
def get_debug_data(info):
    debug_file = info['TestID']['__data__'][0] + '.d_t'
    debug_file = os.path.join(info['basedir'], 'dta', debug_file)
    debug_data = np.array([])
    logging.debug('get_debug_data', debug_file)
    zerodatetime = False
    if os.path.exists(debug_file):
        debug_data, zerodatetime = debug_table(debug_file)
    else:
        logging.error('No diagnostic file:', debug_file)
    return debug_data, zerodatetime

def get_sample_data(info, sample_number):
    fid = info['AllSamplesInformation']['SampleInformation']['SampleFileID']['__data__'][sample_number]
    if fid==' ':
        smp_dir = info['basedir']
    else: 
        smp_dir = os.path.join(info['basedir'], fid)
    segments, shots, results_table = sample_folder(smp_dir)
    return segments, shots, results_table  
    
def columns(info):
    """Parses all sample data referenced in a test information dictionary"""
    smp_info = info['AllSamplesInformation']
    nSamples = int(smp_info['NumberSamples']['__data__'][0])
    samples_data = []  # [(segments0, shots0), (segments1, shots1), ...]
    for n in range(nSamples):
        samples_data.append(get_sample_data(info, n))

    return samples_data




    
    
