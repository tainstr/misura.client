#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Interfaces for local and remote file access"""
import threading
from pickle import loads, dumps
import tempfile
import os
import cStringIO
from traceback import format_exc

from PyQt4 import QtCore

import veusz.document as document
import veusz.plugins as vsplugins

from misura.canon.logger import get_module_logging
from misura.canon.plugin import default_plot_rules

from operation import OperationMisuraImport, ImportParamsMisura, getUsedPrefixes
from proxy import getFileProxy
from decoder import DataDecoder
from model import DocumentModel
from misura.canon.csutil import lockme, incremental_filename
from .. import units
from ..clientconf import confdb
from .. import parameters as params
from misura.client.axis_selection import get_best_x_for
from misura.client.filedata.dataset import MisuraDataset

MAX = 10**5
MIN = -10**5

logging = get_module_logging(__name__)

class MisuraDocument(document.Document):

    """Extended Veusz document with connectivity to a single Misura test file, local or remote"""
    up = False
    zerotime = None
    interval = 1  # Update interval
    instrument_name = False
    root = False
    sigConfProxyModified = QtCore.pyqtSignal()

    def close(self):
        self.up = False
        for k, d in self.decoders.iteritems():
            logging.debug('Closing decoder', k)
            d.close()
        self.decoders = {}
        for p in self.proxies.itervalues():
            p.flush()
            p.close()

    def __init__(self, filename=False, proxy=False, root=False):
        document.Document.__init__(self)
        self.no_update = set([]) # Skip those datasets
        self.cache = {}  # File-system cache
        self.proxies = {}
        self.proxy = False
        self.proxy_filename = False
        self.header = []
        self.root = root
        # File-system cache dir
        self.cache_dir = tempfile.mkdtemp()
        self._lock = threading.Lock()
        # Available datasets in the output file
        self.available_data = {}
        self.model = DocumentModel(self)

        self.decoders = {}
        if proxy:
            self.proxy = proxy
            self.proxy_filename = proxy.get_path()
            self.up = True
        elif filename:
            self.proxy = getFileProxy(filename, mode='r')
            self.proxy_filename = filename
            self.up = False
        else:
            self.up = False
            return
        if self.proxy_filename:
            self.proxies[self.proxy_filename] = self.proxy
        self.create_proxy_decoders(self.proxy, '0:')
        
    #Table export utils
    def get_column_func(self, name):
        return self.data[name].data
    def get_unit_func(self, name):
        u = getattr(self.data[name], 'unit', '')
        return units.hsymbols.get(u, '')
    def get_verbose_func(self, name):
        return getattr(self.data[name], 'm_label', '')

    def create_proxy_decoders(self, proxy, prefix=False):
        """Create one decoder for each relevant dataset in proxy"""
        dec = proxy.header(
            ['Binary', 'Profile', 'CumulativeProfile', 'Image', 'ImageM3', 'ImageBMP'])
        logging.debug('FOUND FOLDERS', dec)
        proxy_path = proxy.get_path() + ':'
        if not prefix:
            files = getUsedPrefixes(self)
            linked = files[proxy_path]
            prefix = linked.prefix
        for fold in dec:
            d = DataDecoder(self)
            d.reset(proxy, datapath=fold, prefix=prefix)
            self.decoders[prefix + fold[1:]] = d
        return True

    def create_decoders(self):
        """Create decoders for each file"""
        files = getUsedPrefixes(self)
        for path, linked in files.iteritems():
            do = True
            for dec in self.decoders.itervalues():
                if dec.proxy.get_path() == path:
                    logging.debug('Already defined decoders for', path)
                    do = False
                    break
            if not do:
                continue
            proxy = getFileProxy(path, mode='r')
            self.create_proxy_decoders(proxy, linked.prefix)

    def add_cache(self, ds, name, overwrite=True):
        """Writes the dataset `ds` onto an filesystem cache. 
        The caller must empty `ds` from any data in order to free memory"""
        if name in self.cache:
            if not overwrite:
                return False
            filename = self.cache[name]
        else:
            filename = os.path.join(
                self.cache_dir, '{}.dat'.format(len(self.cache)))
            filename = incremental_filename(filename)
        
        self.cache[name] = filename
        if hasattr(ds, 'document'):
            del ds.document
        ds.m_name = name
        open(filename, 'wb').write(dumps(ds))
        logging.debug('Cached', name, filename)
        self.available_data[name] = ds
        ds.document = self
        return True

    def get_cache(self, name):
        if self.data.has_key(name):
            return self.data[name]
        filename = self.cache.get(name, False)
        if not filename or not os.path.exists(filename):
            logging.debug('No dataset in cache', name, filename)
            return False
        ds = loads(open(filename, 'rb').read())
        ds.document = self
        # Restore correct linked instances
        if ds.linked and ds.linked.filename:
            p = getUsedPrefixes(self)
            ds.linked = p[ds.linked.filename]
        return ds

    def load_rule(self, filename, rule, **kw):
        op = OperationMisuraImport.from_rule(
            rule, filename, **kw)
        self.applyOperation(op)
        r = op._outdatasets
        del op._outdatasets
        return r

    def _load(self, path, filename, **kw):
        """Load or reload a dataset"""
        op = OperationMisuraImport.from_dataset_in_file(path, filename, **kw)
        self.applyOperation(op)

    def reconnect(self):
        if not self.up:
            return
        self.proxy.close()
        self.proxy = self.proxy.copy()
        self.proxy.connect()

    @lockme()
    def reloadData(self, update=True):
        # Clear all previous datasets, in order to avoid duplicates
        self.zerotime = None
        if not self.up:
            logging.debug('No up', self.up)
            return []
        # Save current units and delete datasets
        self.model.paused = True
        for name in self.data.keys():
            self.deleteData(name)
        self.model.paused = False
        if self.proxy_filename is False:
            logging.debug('no filename defined')
            self.reloading = False
            return []
        logging.debug('Reloading Data', self.proxy_filename)
        rule_load = confdb['rule_load'] + '\n' + confdb['rule_plot']
        for gen_rule_func in default_plot_rules.itervalues():
            rule = gen_rule_func(confdb, self.proxy.conf)
            if not rule:
                continue
            rule_load += '\n' + rule
        op = OperationMisuraImport(
            ImportParamsMisura(filename=self.proxy_filename,
                               time_interval=self.interval,
                               rule_exc=confdb['rule_exc'],
                               rule_inc=confdb['rule_inc'],
                               rule_load=rule_load,
                               rule_unit=confdb['rule_unit'])
        )
        logging.debug('reloadData: apply operation')
        self.applyOperation(op)
        if not self.proxy:
            self.proxy = op.proxy
#       self.proxy.reopen() # apply will close it!
        dsnames = op.outdatasets
        logging.debug('reloadData dsnames', dsnames.keys())

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
            logging.debug('No data loaded in document', self.data)
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
                logging.debug('Non-uniform length found:', col, len(a))
                v = a[-1]
            else:
                v = a[idx]
            meta[col] = v
        return meta

    auto_changeset = 0

    @lockme()
    def update(self, proxy=False):
        if not self.up:
            return []
        if not proxy:
            proxy = self.proxy
        if not self.data.has_key('0:t'):
            logging.debug('Time dataset is missing. Reloading.', self.data.keys())
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
            logging.debug('Update not needed', elp, lastt)
            return []
        logging.debug('Update needed: %.2f>%.2f doc' % (elp, lastt))
        # New time point in time units
        nt = [units.Converter.convert('second', tu, elp)]
        k = []
        header = self.proxy.header(['Array', 'FixedTimeArray'], '/summary')
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

        header_autoupdate = False
        if header_autoupdate and len(dh) > 0:
            logging.debug('RELOADING DATA: HEADER DIFFERS. Missing:', dh)
            logging.debug('header', header)
            logging.debug('keys', ks)
            self._lock.release()
            dsnames = self.reloadData()
            self._lock.acquire(False)
            return dsnames

        # Avoid firing individual updates
        self.suspendUpdates()
        for col in self.data.keys():
            if col in self.no_update:
                continue
            ds = self.data[col]
            if len(ds.data) == 0:
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
                if val is None:
                    self.no_update.add(col)
                    continue
                from_unit = obj.getattr(opt, 'unit')
                to_unit = ds.unit
                # Percentage scaling is active
                if getattr(ds, 'm_percent', False) and ds.m_initialDimension:
                    val *= 100. / ds.m_initialDimension
                # Perform unit conversion
                elif to_unit and to_unit != from_unit:
                    val = units.Converter.convert(from_unit, to_unit, val)
                updata = [val]
                logging.debug('Updating', col, opt, updata, from_unit, to_unit)
                
            N = len(ds.data)
            ds.insertRows(N, 1, {'data': updata})
            k.append(col)
        # Restore firing updates
        self.auto_changeset = self.changeset
        self.enableUpdates()
        self.emit(QtCore.SIGNAL('updated()'))
        return k
    
    def save_plot(self, proxy, plot_id, page=0, name=False, text=False):
        if not name:
            name = plot_id
        if not text:
            text = cStringIO.StringIO()
            self.saveToFile(text)
            text = text.getvalue()
        
        ci = document.CommandInterface(self)   
        tmp = os.path.join(params.pathTmp, 'export.jpg')
        if os.path.exists(tmp):
            os.remove(tmp)
        # Touch the file
        open(tmp, 'w').close()
        mx = len(self.basewidget.children)-1
        if page>mx:
            page = mx
        ci.Export(tmp, page=page)
        render = open(tmp, 'rb').read()
        if not len(render):
            logging.debug('Failed rendering')
            render = False
        r = proxy.save_plot(
            text, plot_id=plot_id, title=name, render=render, render_format='jpg')
        os.remove(tmp)
        return r, text
    
    def iter_data_and_cache(self):
        """Iterate through all datasets and all cached datasets, yielding name, ds"""
        for name, ds in self.data.iteritems():
            yield name, ds
        for name in self.cache.keys():
            ds = self.get_cache(name)
            if ds is False:
                continue
            logging.debug('Saving cached dataset', name)
            yield name, ds
    
    def save_version_and_plot(self, version_name, vsz_text=False):
        plots = set([])  # filename where plot is already saved
        proxies = {}
        for name, ds in self.iter_data_and_cache():
            if not ds.linked or not os.path.exists(ds.linked.filename):
                logging.debug('Skipping unlinked dataset', name, ds.linked)
                continue
            is_local = name[-2:] in ('_t', '_T')
            vfn = ds.linked.filename
            node = self.model.tree.traverse(name)
            conf = node.parent.get_configuration()
            # Exclude dataset not linked to any real option, except local t,T ds
            if (not conf or not conf.has_key(node.name())) and not is_local:
                logging.debug('Skipping invalid dataset:', name, node.name())
                continue
            proxy, proxy_version = proxies.get(vfn, (False, version_name))
            # Ensure conf is saved into proper version
            if proxy is False:
                proxy = self.proxies.get(vfn, False)
                if proxy is False:
                    proxy = getFileProxy(vfn, version=None, mode='a')
                self.proxies[vfn] = proxy
                # Use pre-existing version_name
                version_id = proxy.get_version_by_name(version_name)
                # Otherwise use latest loaded version
                if not version_id:
                    vid = proxy.get_version()
                    # Keep current version when possible
                    if vid!='':
                        proxy_version = proxy.get_versions().get(vid, (version_name,))[0]
                # Create a new version or load existing one
                version_id = proxy.create_version(proxy_version, overwrite=True)
                # Load proper conf version
                proxy.save_conf(node.linked.conf.tree())
                proxies[vfn] = proxy, proxy_version
            if vfn not in plots:
                #TODO: detect current page
                r, vsz_text = self.save_plot(proxy, version_name, text=vsz_text)
                plots.add(vfn)
            if name[-2:]=='_t':
                time_name = 't'
                time_ds = ds
            else:
                time_name = get_best_x_for(name, ds.linked.prefix, self.data.keys()+self.cache.keys(), '_t')
                time_ds = self.get_cache(time_name)
            # Ensure time is in seconds
            time_data = units.Converter.convert(time_ds.unit, 'second', time_ds.data)
            logging.debug('Writing dataset', name)
            proxy.save_data(name, ds.data, time_data, opt=ds.m_opt)
        return True

    def save(self, filename, mode='vsz'):
        """Override Document.save to include version and plot"""
        try:
            r = document.Document.save(self, filename, mode)
            version_name = get_version_name(filename)
            vsz_text = open(filename, 'rb').read()
            r = self.save_version_and_plot(version_name, vsz_text)
        except:
            logging.critical(format_exc())
            raise
        return r        
        
                
                
def get_version_name(vsz):
    return os.path.basename(vsz).replace('.vsz', '')   

def print_history(lst, j=1, ids=False):
    if ids is False:
        ids = {}
    i = -1
    for i, op in enumerate(lst):
        print j + i + 1, op
        ids[id(op)] = op
        j, ids = print_history(getattr(op, 'operations', []), j, ids)
    return j + i + 1, ids
