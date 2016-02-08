#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Interfaces for local and remote file access"""
from misura.canon.logger import Log as logging
from time import sleep
from PyQt4 import QtCore
import threading

import veusz.document as document

from operation import OperationMisuraImport, ImportParamsMisura
from proxy import getFileProxy
from decoder import DataDecoder
from model import DocumentModel
from misura.canon.csutil import lockme
from .. import units
from ..clientconf import confdb
MAX = 10**5
MIN = -10**5


class MisuraDocument(document.Document):

    """Extended Veusz document with connectivity to a single Misura test file, local or remote"""
    up = True
    zerotime = None
    interval = 1  # Update interval
    instrument_name = False
    root = False

    def close(self):
        self.up = False
        for k, d in self.decoders.iteritems():
            print 'Closing decoder', k
            d.close()
        self.decoders = {}

    def __init__(self, filename=False, proxy=False, root=False):
        document.Document.__init__(self)
        self._lock = threading.Lock()
        self.proxy = False
        self.filename = False
        self.header = []
        self.root = root
        # Available datasets in the output file
        self.available_data = {}
        self.model = DocumentModel(self)
        # Create one decoder for each 'dat' group
        self.decoders = {}
        if proxy:
            self.proxy = proxy
            self.filename = proxy.get_path()
        elif filename:
            self.proxy = getFileProxy(filename)
            self.filename = filename
        else:
            up = False
            return

        dec = self.proxy.header(['Binary', 'Profile','Image','ImageM3','ImageBMP'])
        logging.debug('%s %s', 'FOUND FOLDERS', dec)
        for fold in dec:
            d = DataDecoder(self)
            d.reset(self.proxy, datapath=fold)
            self.decoders[fold] = d

    def reconnect(self):
        if not self.up:
            return
        self.proxy.close()
        self.proxy = self.proxy.copy()
        self.proxy.connect()

    @lockme
    def reloadData(self, update=True):
        # Clear all previous datasets, in order to avoid duplicates
        self.zerotime = None
        if not self.up:
            logging.debug('%s %s', 'No up', self.up)
            return []
        # Save current units and delete datasets
        self.model.paused = True
        for name in self.data.keys():
            self.deleteData(name)
        self.model.paused = False
        if self.filename is False:
            logging.debug('%s', 'no filename defined')
            self.reloading = False
            return []
        logging.debug('%s %s', 'Reloading Data', self.filename)

        op = OperationMisuraImport(
            ImportParamsMisura(filename=self.filename,
                               time_interval=self.interval,
                               rule_exc=confdb['rule_exc'],
                               rule_inc=confdb['rule_inc'],
                               rule_load=confdb[
                                   'rule_load'] + '\n' + confdb['rule_plot'],
                               rule_unit=confdb['rule_unit'])
        )
        logging.debug('%s', 'apply operation')
        self.applyOperation(op)
        if not self.proxy:
            self.proxy = op.proxy
#       self.proxy.reopen() # apply will close it!
        dsnames = op.outdatasets
        logging.debug('%s %s', 'reloadData dsnames', dsnames.keys())

        self.emit(QtCore.SIGNAL('updated()'))
        self.emit(QtCore.SIGNAL('reloaded()'))
        self.header = dsnames
        self.model.refresh()
        return dsnames

    def get_row(self, idx):
        """Get a dictionary containing all updated values."""
        if not self.up:
            return {}
        cols = self.data.keys()
        if len(cols) == 0:
            logging.debug('%s %s', 'No data loaded in document', self.data)
            self.reloadData()
            return False
        if len(self.data['0:t']) < idx:
            self.update()
        meta = {}
        for col in cols:
            v = 0
            ds = self.data[col]
            if not ds.m_update:
                continue
            a = ds.data
            if len(a) <= idx:
                logging.debug(
                    '%s %s %s', 'Non-uniform length found:', col, len(a))
                v = a[-1]
            else:
                v = a[idx]
            meta[col] = v
        return meta

    @lockme
    def update(self, proxy=False):
        if not self.up:
            return []
        if not proxy:
            proxy = self.proxy
        if not self.data.has_key('0:t'):
            logging.debug(
                '%s %s', 'Time dataset is missing. Reloading.', self.data.keys())
            self._lock.release()
            dsnames = self.reloadData()
            self._lock.acquire(False)
            return dsnames
            # return []
        self.proxy.connect()
        if not self.root:
            self.root = self.proxy.root
        root = self.root
        root.connect()
        if not self.instrument_name:
            self.instrument_name = self.proxy.conf['runningInstrument']
        instr = getattr(self.proxy.conf, self.instrument_name)
        lastt = self.data['0:t'].data[-1]
        tu = getattr(self.data['0:t'], 'unit', 'second')
        lastt = units.Converter.convert(tu, 'second', lastt)
        if self.zerotime is None:
            self.zerotime = instr['zerotime']
        elp = root.time() - self.zerotime
        # interval rounding
        elp = (elp // self.interval) * self.interval
        if (elp - lastt) < self.interval:
            logging.debug('%s %s %s', 'Update not needed', elp, lastt)
            return []
        logging.debug('Update needed: %.2f>%.2f doc' % (elp, lastt))
        # New time point in time units
        nt = [units.Converter.convert('second', tu, elp)]
        k = []
        header = self.proxy.header(['Array'], '/summary')
        for h in header[:]:
            r = confdb.rule_dataset(h, latest=True)
            if r:
                r = r[0]
            if r == 1:
                header.remove(h)
        header = [h.replace('/summary/', '0:')
                  for h in header]  # remove initial /
        header = set(header)
        ks = set(self.data.keys()) | set(self.available_data.keys())
        dh = header - ks

        temporary_disabled = False
        if temporary_disabled and len(dh) > 0:
            logging.debug(
                '%s %s', 'RELOADING DATA: HEADER DIFFERS. Missing:', dh)
            logging.debug('%s %s', 'header', header)
            logging.debug('%s %s', 'keys', ks)
            self._lock.release()
            dsnames = self.reloadData()
            self._lock.acquire(False)
            return dsnames

        for col in self.data.keys():
            ds = self.data[col]
            if len(ds.data) == 0:
                #               print 'Skipping empty',col,ds.m_col
                continue
            if not getattr(ds, 'm_col', False):
                # Not a misura dataset
                continue
            if col == '0:t':
                updata = nt
            else:
                # Ask last point
                obj, opt = root.from_column(ds.m_col)
                val = obj[opt]
                from_unit = obj.getattr(opt, 'unit')
                to_unit = ds.unit
                # Percentile scaling is active
                if getattr(ds, 'm_percent', False):
                    val *= 100. / ds.m_initialDimension
                # Perform unit conversion
                elif to_unit and to_unit != from_unit:
                    val = units.Converter.convert(from_unit, to_unit, val)
                updata = [val]
                logging.debug(
                    '%s %s %s %s %s %s', 'Updating', col, opt, updata, from_unit, to_unit)
            N = len(ds.data)
            ds.insertRows(N, 1, {'data': updata})
            k.append(col)
        self.emit(QtCore.SIGNAL('updated()'))
        return k
