#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Interfaces for local and remote file access"""
import threading
import tempfile
import os
import cStringIO
from traceback import format_exc
from compiler.ast import flatten
import gc

from PyQt4 import QtCore
from tables.file import _open_files
import numpy as np

import veusz.document as document
import veusz.plugins as vsplugins
from veusz.utils import iter_widgets

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
from misura.client.live import registry
from misura.client.iutils import get_plotted_tree, memory_check

MAX = 10**5
MIN = -10**5

logging = get_module_logging(__name__)

def list_datasets_in_page(page):
    datasets = set()
    for curve in iter_widgets(page, 'xy', 1):
        if not curve:
            continue
        datasets.add(curve.settings.xData)
        datasets.add(curve.settings.yData)
    return datasets

class MisuraDocument(document.Document):

    """Extended Veusz document with connectivity to a single Misura test file, local or remote"""
    up = False
    zerotime = None
    interval = 1  # Update interval
    instrument_name = False
    root = False
    changeset_ignore = 0
    sigConfProxyModified = QtCore.pyqtSignal()
    sig_save_started = QtCore.pyqtSignal()
    sig_save_done = QtCore.pyqtSignal()
    
    @property
    def tasks(self):
        return getattr(registry, 'tasks', False)

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
        self.cached_pages = set()
        self.accessed_pages = []
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
        dec = proxy.header(['Binary', 'Profile', 'CumulativeProfile', 'Image', 
                            'ImageM3', 'ImageBMP'])
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
            #FIXME: this causes double loading of /conf node!!!
            proxy = getFileProxy(path, mode='r', load_conf=False)
            self.create_proxy_decoders(proxy, linked.prefix)

    def add_cache(self, ds, name, overwrite=True):
        """Writes the dataset `ds` onto the filesystem cache. 
        """
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
            ds.document = None
        ds.m_name = name
        # Separate data attributes
        data = []
        for col in ds.columns:
            data.append(getattr(ds, col))
            if data[-1] is not None:
                setattr(ds, col, np.array([]))
        o = open(filename, 'wb')
        np.save(o, data)
        o.close()
        ##o.write(dumps(data))
        logging.debug('Cached', name, filename)
        self.available_data[name] = ds
        ds.document = self
        return True

    def get_cache(self, name, load_data=True, add_to_doc=False):
        if self.data.has_key(name):
            return self.data[name]
        filename = self.cache.get(name, False)
        if not filename or not os.path.exists(filename):
            logging.debug('No dataset in cache', name, filename)
            return False
        # Retrieve dataset from available cache
        ds = self.available_data[name]
        # Restore correct linked instances
        if ds.linked and ds.linked.filename:
            p = getUsedPrefixes(self)
            ds.linked = p[ds.linked.filename]
        if not load_data:
            return ds
        # Restore data attributes
        data = np.load(open(filename, 'rb'))
        #data = loads(open(filename, 'rb').read())
        for i, col in enumerate(ds.columns):
            setattr(ds, col, data[i])
        if add_to_doc:
            self.data.pop(name, False)
            self.available_data.pop(name, False)
            self.data[name] = ds
            
        return ds
    
    
    def cache_page(self, name):
        """Empty all datasets which are unique to page `name`"""
        if name.startswith('/'):
            name = name[1:]
        if name in self.cached_pages:
            logging.debug('Cannot cache_page again', name)
            return False
        
        page = self.basewidget.getChild(name)
        datasets = list_datasets_in_page(page)
        
        # List all datasets acting as sources to plugin-datasets
        plotted = get_plotted_tree(self.basewidget)
        sources = set()
        plotted_datasets = set(plotted['dataset'].keys()+plotted['xdataset'].keys())
        for dataset_name, dataset in self.data.items():
            # Skip non-plugins
            if not hasattr(dataset, 'pluginmanager'):
                # If dataset is not plotted anywere, it is eligible for caching
                if dataset_name not in plotted_datasets and len(dataset.data):
                    datasets.add(dataset_name)
                continue
            sources += set(flatten(dataset.pluginmanager.fields.values()))
        
        # Set page as cached
        self.cached_pages.add(name)
        if name in self.accessed_pages:
            self.accessed_pages.remove(name)
        
        # Remove any dataset not used in other pages
        for dataset_name in list(datasets):
            N = len(self.data[dataset_name].data)
            rem = False
            if dataset_name in sources:
                # Do not cache datasets which are source of plugins
                rem = True
            if dataset_name in self.cache and N==0:
                logging.warning('Page contained an already cached dataset', dataset_name)
                rem = True
            if not N:
                # Do not cache empty datasets
                rem = True
            
            if rem:
                datasets.remove(dataset_name)
                continue
            
            # Remove dataset plotted somewhere else
            if dataset_name not in plotted_datasets:
                continue
            # Set of curves involving this dataset
            involved_pages = set(plotted['dataset'].get(dataset_name,[])+plotted['xdataset'].get(dataset_name,[]))
            # Convert to set page names
            involved_pages = set([page.split('/')[1] for page in involved_pages])
            # Select only pages which are not already cached
            involved_pages = involved_pages.difference(self.cached_pages)
            if len(involved_pages)>0:
                logging.debug('Not caching', dataset_name, involved_pages)
                datasets.remove(dataset_name)
        
        # Cache remaining datasets
        for dataset_name in datasets:
            dataset = self.data[dataset_name]
            self.add_cache(dataset, dataset_name, overwrite=True)
            logging.debug('cached', dataset_name, len(dataset.data))
            
        if len(datasets):
            self.setModified(True)
        return True
            
    def retrieve_page(self, name):
        """Retireve from cache any dataset in page `name`"""
        if name.startswith('/'):
            name = name[1:]
        if name not in self.cached_pages:
            logging.debug('retrieve_page: page not cached', name)
            return False
        page = self.basewidget.getChild(name)
        datasets = list_datasets_in_page(page)
        n = 0
        for dataset_name in datasets:
            if not dataset_name in self.cache:
                logging.debug('retrieve_page: not cached', dataset_name)
                continue
            
            old_ds = self.data.pop(dataset_name, False)
            self.get_cache(dataset_name, add_to_doc=True)
            logging.debug('retrieve_page: loaded', dataset_name)
            n+=1
        self.cached_pages.remove(name)
        if n>0:
            self.setModified(True)
        return True
    
    def manage_page_cache(self, active_page_name=False):
        if active_page_name in self.cached_pages:
            self.retrieve_page(active_page_name)
        if active_page_name:
            if active_page_name in self.accessed_pages:
                self.accessed_pages.remove(active_page_name)
            self.accessed_pages.append(active_page_name) 
        
        n = 0
        while len(self.accessed_pages)>1 and memory_check(warn=False)[0]:
            self.cache_page(self.accessed_pages.pop(0))
            n+=1
        if n:
            logging.debug('Wiping document history')
            self.clearHistory()
            gc.collect()
        
        

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
        keys = []
        # Move local keys to the end of the iteration
        # (used during save operations)
        for k in self.cache.keys():
            if k[-2:] in ('_t','_T'):
                keys.append(k)
            else:
                keys.insert(0, k)
        for name in keys:
            ds = self.get_cache(name)
            if ds is False:
                continue
            logging.debug('Saving cached dataset', name)
            yield name, ds
    
    def save_version_and_plot(self, version_name, vsz_text=False, pid=False):
        plots = set([])  # filename where plot is already saved
        proxies = {}
        pid = pid or 'Save: {}'.format(version_name)
        self.sig_save_started.emit()
        excluded_datasets = set()
        if self.tasks is not False:
            self.tasks.jobs(len(self.data)+len(self.cache), pid)
        for i, (name, ds) in enumerate(self.iter_data_and_cache()):
            if self.tasks is not False:
                self.tasks.job(i, pid, name)
            if not ds.linked or not os.path.exists(ds.linked.filename):
                logging.debug('Skipping unlinked dataset', name, ds.linked)
                continue
            if getattr(ds.linked, 'mtype', False)!='LinkedMisuraFile':
                logging.debug('Skipping non-misura dataset', name, ds.linked)
                continue
            is_local = name[-2:] in ('_t', '_T')
            vfn = os.path.abspath(ds.linked.filename)
            node = self.model.tree.traverse(name)
            conf = node.parent.get_configuration()
            # Exclude dataset not linked to any real option, except local t,T ds
            if (not conf or not conf.has_key(node.name())) and not is_local:
                logging.debug('Skipping invalid dataset:', name, node.name())
                excluded_datasets.add(name)
                continue
            proxy, proxy_version = proxies.get(vfn, (False, version_name))
            # Ensure conf is saved into proper version
            if proxy is False:
                logging.debug('save_version_and_plot: checking', vfn)
                proxy = self.proxies.get(vfn, False)
                if proxy is False:
                    logging.debug('save_version_and_plot: reopening', vfn)
                    proxy = getFileProxy(vfn, version=None, mode='a')
                # Might fail to open readwrite if already opened readonly:
                if proxy.test is False:
                    for h in list(_open_files.get_handlers_by_name(vfn)):
                        logging.debug('Closing all handlers:', id(h), h.mode, vfn)
                        h.close()
                    logging.debug('save_version_and_plot: reopening', vfn)
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
                # TODO: keep those at the end of the iteration!
            if name[-2:]=='_t':
                if name in excluded_datasets:
                    logging.debug('Excluding an already associated time dataset', name)
                    continue
                time_name = 't'
                time_ds = ds
            else:
                time_name = get_best_x_for(name, ds.linked.prefix, self.data.keys()+self.cache.keys(), '_t')
                time_ds = self.get_cache(time_name)
                excluded_datasets.add(time_name)
            # Ensure time is in seconds
            time_data = units.Converter.convert(time_ds.unit, 'second', time_ds.data)
            logging.debug('Writing dataset', name)
            proxy.save_data(name, ds.data, time_data, opt=ds.m_opt)
        if not proxy:
            return True
        proxy.header(refresh=True)
        proxy.flush()
        self.sig_save_done.emit()
        if self.tasks:
            self.tasks.done(pid)
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
    
    def set_linked_version(self, filename, version):
        """Set the new version for a file proxy"""
        linkedfiles = set()
        for name, ds in self.data.items():
            if ds.linked and ds.linked.params.filename==filename:
                logging.debug('Resetting version', ds, name, version)
                ds.linked.params.version = version
                ds.linked.params.version=version
                linkedfiles.add(ds.linked)
                
        if not len(linkedfiles):
            logging.debug('No dataset found at the required version', version)
            return False
        self.model.pause(True)
        for linked in linkedfiles:
            logging.debug('Reloading links', linked)
            r = linked.reloadLinks(self)
        self.model.pause(False)
        self.setModified()
        return True    
        
                
                
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
