#!/usr/bin/python
# -*- coding: utf-8 -*-
"""FlashLine Debug Files parser (dta/.log, .clog, .d_d, .d_g, .d_c, .d_l, etc)"""
import glob
import numpy as np
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

supported_extensions = ['clog', 'd_c', 'd_d', 'd_f', 'd_g', 'd_h', 'd_l', 'd_t', 'd_Thread', 'log']

minimum_line_length = 1 + 10 + 1 # rt, t, msg

def parse_log_line(line):
    line = line.replace('  ', ' ').replace('  ', ' ').replace('\n','')
    if len(line)<minimum_line_length:
        return False
    line = line.split(' ')
    line = filter(lambda e: e!='', line)
    # Pop relative time
    if len(line[0])<8:
        line.pop(0)
    try:
        t = float(line[0])
    except:
        logging.debug('skip', line)
        return False
    msg = ' '.join(line[1:])
    return t, msg
    
def differentiate_equal_times(vt):
    start = -1
    for i, t in enumerate(vt):
        if i==0:
            continue
        if t==vt[i-1]:
            if start < 0:
                start = i-1
                continue
        elif start>=0:
            end = i
            vt[start:end]+=np.linspace(0, 1, 1+end-start)[:-1]
            start = -1
    return vt
        
def parse_log_file(filename, show_ext=False):
    logging.debug('parse_log_file', filename)
    ext = filename.split('.')[-1]+': '
    f = open(filename, 'r')
    vt = []
    vmsg  = []
    for line in f.readlines():
        line = parse_log_line(line)
        if not line:
            continue
        vt.append(line[0])
        msg = line[1]
        if show_ext:
            msg = ext+msg
        vmsg.append(msg)
    # Differentiate equal times
    vt = differentiate_equal_times(vt)
    logging.debug('parse_log_file', filename, len(vt))
    return vt, vmsg
    
def parse_all_logs(dta):
    """Parses all supported log files and returns time and message arrays sorted by time"""
    logging.debug('parse_all_logs', dta)
    vt = []
    vmsg = []
    for ext in supported_extensions:
        for fn in glob.glob(dta+'*.'+ext):
            rt, rmsg = parse_log_file(fn, show_ext=True)
            vt += rt
            vmsg += rmsg
    vt = np.array(vt).astype(float)
    vmsg = np.array(vmsg).astype(str)
    m = np.argsort(vt)
    logging.debug('parse_all_logs', dta, len(vt))
    return vt[m], vmsg[m]
            