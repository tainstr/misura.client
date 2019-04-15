#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Test FlashLine import recursively from a starting folder"""
from time import time
import os
import shutil
from traceback import format_exc
import logging, logging.handlers
import multiprocessing
from misura.canon.logger import Log as log

from thegram.flashline import Converter
from misura.client.clientconf import confdb
from veusz.widgets import root

#source = 'Z:\Thermophysical Instrument Data\TPP Manufacturing Data\DLF1200\DLF1200-0046 (DLF1-0046 & 12EM-0046)'
source = 'C:\\Users\\rhebling\\Desktop\\More Test Data\\Instrument Data From PC'
dest = os.path.join(os.path.expanduser("~"), 'Desktop\\flashline_crawler\\DLF1200')
dest = 'C:\\Users\\rhebling\\Desktop\\flashline_crawler\\DLF1200'

copying_folders = False

copy_back = True # overwrite source .h5 files
fail_fast = True
resume = True

# Logging parameters
logsize = 12e6
logBackupCount = 10
logLevel = -1
xml = 'TestInformation.xml'

if not os.path.exists(dest):
    os.makedirs(dest)

# Configure logging
log_file = os.path.join(dest, 'output.log')

handler = logging.FileHandler(
    log_file)
handler.setFormatter(
    logging.Formatter("%(levelname)s: %(asctime)s %(message)s"))
logging.getLogger().addHandler(handler)
stream = logging.StreamHandler()
stream.setFormatter(
    logging.Formatter("%(levelname)s: %(asctime)s %(message)s"))
logging.getLogger().addHandler(stream)
logging.getLogger().setLevel(logLevel)


# Crawler Function
def do(testinfo):
    log.info('Converting', testinfo)
    cvt = Converter()
    cvt.confdb = confdb
    outpath = cvt.get_outpath(testinfo)
    if os.path.exists(outpath) and resume:
        return 'SKIP'
    cvt.convert(testinfo)
    return cvt.outpath
    #TODO: import in a veusz document and verify
        
def exclude_h5(root, files):
    return filter(lambda name: name.endswith('.h5'), files)

# Crawler loop
if __name__== '__main__':
    multiprocessing.freeze_support()
    
    failures = open(os.path.join(dest, 'failures.log'), 'w')
    
    for root, dirs, files in os.walk(source):
        if xml not in files:
            log.debug('Skipping:', root)
            continue
        relative = os.path.relpath(root, source)
        if copying_folders:
            out_dir = os.path.join(dest, relative)
        else:
            out_dir = root
        
        out_testinfo = os.path.join(out_dir, xml)
        if "DLF1600_PP14_SSVT" in out_testinfo or "High" in out_testinfo or "Low" in out_testinfo or "525" in out_testinfo or "393" in out_testinfo:
            continue
        # Copy files before importing
#         if not os.path.exists(out_dir) or not os.path.exists(out_testinfo):
#             out_parent = os.path.join(dest, relative)
#             log.debug('copytree', root, out_parent)
#             shutil.copytree(root, out_parent, ignore=exclude_h5)
#         else:
#             log.debug('NO COPYTREE', out_dir, out_testinfo)
        outpath = ''
        try:
            #cvt = Converter()
            #outpath = cvt.get_outpath(out_testinfo)
            outpath = do(out_testinfo)
            if outpath == 'SKIP':
                continue
        except KeyboardInterrupt:
            break
        except:
            log.critical('Failed conversion:', root)
            exc = format_exc()
            log.error(exc)
            failures.write('PATH: '+root+'\n')
            failures.write(exc+'\n')
            failures.flush()
        if not outpath or not os.path.exists(outpath):
            log.critical('Failed conversion:', outpath, root, outpath)
            if os.path.exists(outpath):
                log.info('Removing stale file:', root, outpath)
                os.remove(outpath)
            if fail_fast:
                break
            continue
        # Coby back converted file
        #relative = os.path.relpath(outpath, dest)
#         source_h5 = os.path.join(source, relative)
#         if not os.path.exists(source_h5) or copy_back:
#             log.info('Copy back:', outpath, source_h5)
#             shutil.copy(outpath, source_h5)
            
    failures.close()
        
    