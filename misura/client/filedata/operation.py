#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Import a Misura h5 file or remote live test into Veusz document."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from exceptions import BaseException
import numpy as np
from copy import deepcopy
import re
from scipy.interpolate import InterpolatedUnivariateSpline, interp1d

import veusz.dataimport.base as base

from misura.canon import option
from misura.canon.option.common_proxy import from_column

from dataset import MisuraDataset, Sample
import linked
from proxy import getFileProxy

from entry import iterpath

from .. import iutils, live
from .. import clientconf
from .. import _
from .. import units
from ..axis_selection import get_best_x_for


from PyQt4 import QtCore
from misura.canon.plugin import default_plot_rules


sep = '/'

class EmptyDataset(BaseException):
    pass


def getUsedPrefixes(doc):
    p = {}
    for name, ds in doc.data.iteritems():
        lf = ds.linked
        if lf is None:
            logging.debug('no linked file for ', name)
            continue
        p[lf.filename] = lf
    logging.debug('getUsedPrefixes', p, doc.data.keys())
    return p

VERSION_LATEST = -1
VERSION_UNSET = -2

def get_linked(doc, params, create=True):
    opf = getUsedPrefixes(doc)
    # Find if the filename already has a prefix
    lf = opf.get(params.filename, False)
    if lf is not False:
        return lf
    if not create:
        return False
    # Find a new non-conflicting prefix
    prefix = params.prefix
    used = [lf.prefix for lf in opf.values()]
    while prefix in used:
        base, n, pre = iutils.guessNextName(prefix[:-1])
        prefix = pre + ':'
        print('get_linked guess', prefix)
    params.prefix = prefix
    params.version = VERSION_LATEST
    LF = linked.LinkedMisuraFile(params)
    LF.prefix = prefix
    logging.debug('get_linked', prefix, params.filename)
    LF.conf = False
    return LF



class ImportParamsMisura(base.ImportParamsBase):

    """misura import parameters.

    additional parameters:
     reduce: reduce the number of points.
     reducen: target number of points
    """
    defaults = deepcopy(base.ImportParamsBase.defaults)
    defaults.update({
        'prefix': '0:',
        'uid': '',
        'version': VERSION_UNSET,  # means not set
        'reduce': False,
        'reducen': 1000,
        'time_interval': 1,  # interpolation interval for time coord
        'time_unit': 'second', # Convert time datasets to this unit
        'rule_exc': clientconf.rule_exc,
        'rule_inc': clientconf.rule_inc,
        'rule_load': clientconf.rule_load,
        # dynamically generate a load rule based on file contents
        'gen_rule_load': False,
        'rule_unit': clientconf.rule_unit,
        'overwrite': True,
        # keep data within the operation object - no real import to document
        'dryrun': False,
        # rebuild the entire available map
        'rebuild': True
    })


def read_data(proxy, col):
    """Read `col` node from `proxy`"""
    data0 = np.array(proxy.col(col, (0, None)))
    # FIXME: now superfluous?
    # FixedTimeArray
    if data0.shape[1] == 1:
        t0 = proxy.get_node_attr(col, 't0')
        dt = proxy.get_node_attr(col, 'dt')
        n = data0.shape[0]
        t = np.linspace(t0, t0+n*dt, n)
        return np.array([t, data0[:,0]]).transpose()
    else:
        data = data0.view(np.float64).reshape((len(data0), 2))
        data = data[np.isfinite(data[:, 1])]
    return data


def not_interpolated(proxy, col, startt, endt):
    """Retrieve `col` from `proxy` and extend its time range from `startt` to `endt`"""
    logging.debug('not interpolating col', col, startt, endt)
    # Take first point to get column start time
    zt = proxy.col(col, 0)
    if zt is None or zt is False or len(zt) == 0:
        logging.debug('Skipping column: no data', col, zt)
        return False, False
    zt = zt[0]
    data = read_data(proxy, col)
    # Extend towards start
    s = data[0][0]
    # Translate natural times
    # FIXME: used only for old test files!
    if s > 10**8:
        data[0][:] -= s
        s = 0
    if s > startt:
        d = int(s - startt)

        apt = np.linspace(0, d - 1, d)
        vals = np.ones(d) * data[0][1]
        ap = np.array([apt, vals]).transpose()
        data = np.concatenate((ap, data))
    # Extend towards end
    s = data[-1][0]
    d = int(endt - s)
    if d > 2:
        apt = np.linspace(s + 1, endt + 1, d)
        vals = np.ones(d) * data[-1][1]
        ap = np.array([apt, vals]).transpose()
        data = np.concatenate((data, ap))
    return data.transpose()

def memory_saving_interpolation(x,y,x1,k=1):
    """InterpolatedUnivariateSpline is much faster, but less memory efficient.
    Switch between the two according to the dimension of the dataset."""
    if len(x)<1e6:
        try:
            f = InterpolatedUnivariateSpline(x,y,k=k)
        except:
            f = interp1d(x,y)
    else:
        # interp1d is more memory efficient
        f = interp1d(x,y)
    return f(x1)

def interpolated(proxy, col, ztime_sequence):
    """Retrieve `col` from `proxy` and interpolate it around `ztime_sequence`"""
    tdata = not_interpolated(proxy, col, ztime_sequence[0], ztime_sequence[-1])
    if tdata is (False, False):
        return []
    t, val = tdata[0], tdata[1]
    # Empty column
    if val is False or len(val) == 0:
        return val
    r = memory_saving_interpolation(t, val, ztime_sequence)
    return r


def tasks():
    r = getattr(live.registry, 'tasks', False)
    return r


def jobs(n, pid="Reading dataset"):
    # FIXME: causes random crashes while opening microscope tests in compiled
    # win exe
    # return
    t = tasks()
    if t is not False:
        t.jobs(n, pid)


def job(n, pid="Reading dataset", label=''):
    # FIXME: causes random crashes while opening microscope tests in compiled
    # win exe
    # return
    t = tasks()
    if t is not False:
        t.job(n, pid, label)


def done(pid="Reading dataset"):
    # FIXME: causes random crashes while opening microscope tests in compiled
    # win exe
    # return
    t = tasks()
    if t is not False:
        t.done(pid)


def assign_sample_to_dataset(ds, linked_file, reference_sample, hdf_dataset_name):
    """Find out the sample index to which this dataset refers"""
    col = hdf_dataset_name
    obj, var = linked_file.conf.from_column(col)
    if '/sample' in col and reference_sample:
        parts = col.split(sep)
        for q in parts:
            if q.startswith('sample'):
                break
        i = int(q[6:]) + 1
        smp = linked_file.samples[i]
        logging.debug(
            'Assigning sample', i, 'to curve', col, smp, smp.ref, var)
        ds.m_smp = smp
        # Retrieve initial dimension from sample
        if var == 'd':
            ds.m_initialDimension = smp.conf['initialDimension']

    if ds.m_smp is False:
        ds.m_smp = reference_sample
        return False
    return True


def assign_label(ds, col0):
    """Assigns an m_label to the dataset"""
    if 't' in [col0, ds.m_var]:
        ds.m_label = _("Time")
    elif 'T' in [col0, ds.m_var]:
        ds.m_label = _("Temperature")
    elif getattr(ds, 'm_opt', False):
        ds.m_label = _(ds.m_opt["name"])
    else:
        ds_object, ds_name = ds.m_conf.from_column(col0)
        opt = ds_object.gete(ds_name)
        ds.m_label = _(opt["name"])

def get_unit_hdf_attr(fileproxy, hdf_dataset_name, unit_attr):
    u = fileproxy.get_node_attr(hdf_dataset_name, unit_attr)
    if u in ['', 'None', None, False, 0, []]:
        u = False
    elif hasattr(u, '__iter__'):
        # FIXME: if it comes from a table, should parse header and take correct idx!
        column = fileproxy.get_node_attr(hdf_dataset_name, 'column')
        if column in ['', 'None', None, []]:
            column = -1
        u = u[column]
    return u

def dataset_measurement_unit(hdf_dataset_name, fileproxy, data, m_var):
    """Get measurement unit from hdf attribute or guess it for t, T"""
    u = 'None'
    if hdf_dataset_name == 't':
        u = 'second'
    elif len(data):
        # Detect csunit in saved version
        u = get_unit_hdf_attr(fileproxy, hdf_dataset_name, 'csunit')
        if not u:
            # Try default unit
            u = get_unit_hdf_attr(fileproxy, hdf_dataset_name, 'unit')
        # Correct missing celsius indication
        if not u and m_var == 'T':
            u = 'celsius'
    #logging.debug('dataset_measuring_unit', hdf_dataset_name, u)
    return u

def resolve_unit(ds, opt, default):
    """Get unit from RoleIO option"""
    if not opt:
        logging.debug('No OPT', ds.name)
        ds.unit = default
        ds.old_unit = default
        return False
    ds.m_opt = opt
    col = opt.get('column', -1)
    obj, io = option.resolve_role(ds.m_conf, opt)
    io = io or opt
    original_unit = io.get('unit', ds.old_unit)
    client_unit = io.get('csunit', original_unit)
    if client_unit == 'None':
        client_unit = default
    if original_unit == 'None':
        original_unit = client_unit
    if hasattr(client_unit, '__iter__'):
        client_unit = client_unit[col]
    if hasattr(client_unit, '__iter__'):
        original_unit = original_unit[col]
    ds.unit = client_unit
    ds.old_unit = original_unit
    return True
       

def create_dataset(fileproxy, data, prefixed_dataset_name,
                   pure_dataset_name,
                   hdf_dataset_name=False,
                   variable_name=False,
                   m_update=True, p=0,
                   linked_file=False, reference_sample=False,
                   rule_unit=lambda *a: False,
                   unit=False,
                   opt=False):
    # TODO: cleaun-up all this proliferation of *_dataset_names!!!
    #logging.debug('create_dataset', prefixed_dataset_name,
    #              pure_dataset_name, hdf_dataset_name, variable_name)
    # Get meas. unit
    if not unit:
        unit = dataset_measurement_unit(
            hdf_dataset_name, fileproxy, data, variable_name)
    ds = MisuraDataset(data=data, linked=linked_file)
    ds.m_name = prefixed_dataset_name
    ds.m_pos = p
    ds.m_smp = reference_sample
    ds.m_var = variable_name
    ds.m_col = pure_dataset_name
    ds.m_update = m_update
    ds.m_conf = fileproxy.conf
    unit = str(unit) if unit else unit
    if opt:
        resolve_unit(ds, opt, unit)
    else:
        logging.debug('No OPT: keep unit', prefixed_dataset_name, unit)
        ds.unit = unit
        ds.old_unit = unit
    

    # Read additional metadata
    if len(data) > 0 and prefixed_dataset_name[-2:] not in ('_t', '_T', ':t'):
        logging.debug('Reading metadata',  hdf_dataset_name)
        assign_sample_to_dataset(
            ds, linked_file, reference_sample, hdf_dataset_name)
        # Units conversion
        nu = rule_unit(hdf_dataset_name)
        if unit and nu:
            logging.debug('Conveting units:', hdf_dataset_name, unit, nu, ds.unit, ds.old_unit)
            ds = units.convert(ds, nu[0], return_copy=False)
            logging.debug('New dataset unit', ds.unit, ds.old_unit, nu[0])
    elif prefixed_dataset_name.endswith('_t'):
        ds.m_opt = option.ao(
            {}, variable_name, 'Float', 0, 'Time', unit=ds.unit)[variable_name]
    elif prefixed_dataset_name.endswith('_T'):
        ds.m_opt = option.ao(
            {}, variable_name, 'Float', 0, 'Temperature', unit=ds.unit)[variable_name]
        
    # Add the hierarchy tags
    for sub, parent, leaf in iterpath(pure_dataset_name):
        if leaf and parent:
            ds.tags.add(parent)
    if hdf_dataset_name:
        assign_label(ds, hdf_dataset_name)
    #logging.debug('done create_dataset', prefixed_dataset_name,
    #              pure_dataset_name, hdf_dataset_name, variable_name, ds.unit, ds.old_unit)
    return ds


def extend_rule(rule, version=False):
    rule += '|^(/summary/)?' + rule
    if isinstance(version, basestring):
        rule += '|^({}/summary/)?'.format(version) + rule
        rule += '|^({}/)?'.format(version) + rule
    return rule


def prefixed_column_name(col0, prefix):
    #col = col0.replace('/summary/', '/')
    if col0 == 't':
        col = 't'
    else:
        col = '/' + '/'.join(from_column(col0))
    mcol = col
    if mcol.startswith(sep):
        mcol = mcol[1:]
    if mcol.endswith(sep):
        mcol = mcol[:-1]
    pcol = prefix + mcol
    m_var = col.split('/')[-1]
    return pcol, mcol, m_var, col


def cmp_rule(rule):
    """Compile rule if valid"""
    if len(rule) == 0:
        return False, False
    r = rule.replace('\n', '|')
    return r, re.compile(r)


def generate_rule_from_conf(confdb, conf=False, rule=False):
    vrule = []
    for rule_func in default_plot_rules.itervalues():
        r = rule_func(confdb=confdb, conf=conf)
        if r:
            vrule.append(r)
    if len(vrule):
        vrule = '\n'.join(vrule)
        if not rule:
            rule = vrule
        else:
            rule += '\n' + vrule
    return rule, re.compile(rule)


class OperationMisuraImport(QtCore.QObject, base.OperationDataImportBase):

    """Import misura HDF File format. This operation is also a QObject so it can send signals to other objects."""
    descr = 'import misura hdf file'
    proxy = False
    rule_exc = False
    rule_inc = False
    rule_load = False
    _rule_load = False
    rule_unit = False
    instrument = False

    def __init__(self, params):
        """Create an import operation on the filename. Update defines if keep old data or completely wipe it."""

        QtCore.QObject.__init__(self)
        base.OperationDataImportBase.__init__(self, params)
        self.linked = True
        self.filename = params.filename
        self.uid = params.uid
        self.load_rules(params)

    def load_rules(self, params):
        self._rule_exc, self.rule_exc = cmp_rule(params.rule_exc)
        logging.debug('Exclude rule', self._rule_exc)
        self._rule_inc, self.rule_inc = cmp_rule(params.rule_inc)
        logging.debug('Include rule', self._rule_inc)
        self._rule_load, self.rule_load = cmp_rule(params.rule_load)
        logging.debug('Load rule', self._rule_load)
        self.rule_unit = clientconf.RulesTable(params.rule_unit)
        logging.debug('Units rule', self.rule_unit)

    @classmethod
    def from_dataset_in_file(cls, dataset_name, linked_filename, **kw):
        """Create an import operation from a `dataset_name` contained in `linked_filename`"""
        if ':' in dataset_name:
            dataset_name = dataset_name.split(':')[1]

        #rule = '^(/summary/)?' + dataset_name + '$'
        rule = extend_rule(dataset_name + '$', kw.get('version', VERSION_UNSET))
        p = ImportParamsMisura(filename=linked_filename,
                               rule_exc='',
                               rule_load=rule,
                               rule_unit=clientconf.confdb['rule_unit'],
                               **kw)
        op = OperationMisuraImport(p)
        return op

    @classmethod
    def from_rule(cls, rule, linked_filename, **kw):
        """Create an import operation from a `dataset_name` contained in `linked_filename`"""
        version = kw.get('version', VERSION_UNSET)
        kw['version'] = version
        rebuild = kw.get('rebuild', False)
        kw['rebuild'] = rebuild
        rules = rule.splitlines()
        if version:
            for i, rule in enumerate(rules):
                rules[i] = extend_rule(rule, version)
        rule = '|'.join(rules)
        p = ImportParamsMisura(filename=linked_filename,
                               rule_exc='',
                               rule_load=rule,
                               rule_unit=clientconf.confdb['rule_unit'],
                               **kw)
        op = OperationMisuraImport(p)
        return op

    def do(self, document):
        """Override do() in order to get a reference to the document!"""
        self._doc = document
        return base.OperationDataImportBase.do(self, document)

    def get_file_proxy(self):
        """Try to open a FileProxy and a LinkedFile from the parameters (filename and uid)"""
        logging.debug('get_file_proxy',self.uid,self.filename)
        doc = self._doc
        if self.uid:
            new = clientconf.confdb.resolve_uid(self.uid)
            if new:
                logging.debug(
                    'Opening by uid %s: %s instead of %s' % (self.uid, new, self.filename))
                self.filename = new[0]
            else:
                logging.debug('Impossible to resolve uid:', self.uid)
        else:
            logging.debug('No uid defined in params')
        if not self.filename:
            return False
        # Get a the corresponding linked file or create a new one with a new
        # prefix
        LF = get_linked(doc, self.params)
        # Remember linked file configuration
        self.params.prefix = LF.prefix
        self.prefix = LF.prefix
        jobs(3)
        # open the file
        fp = getattr(doc, 'proxy', False)
        logging.debug('FILENAME', self.filename, type(fp), fp)
        if self.params.version==VERSION_UNSET:
            logging.debug('params.version is not set: inheriting from LinkedFile', LF.params.version)
            self.params.version = LF.params.version
        if fp and fp.isopen() and fp.get_version()!=self.params.version:
            logging.debug('Changing version from {} to {}'.format(
                        repr(fp.get_version()), 
                        repr(self.params.version)
                        )
                )
            fp.set_version(self.params.version)
        if fp is False or not fp.isopen():
            logging.debug('Opening a new file proxy', self.filename, repr(self.params.version))
            self.proxy = getFileProxy(
                self.filename, version=self.params.version, mode='r')
        else:
            self.proxy = fp
        job(1, label='Configuration')
        if not self.proxy.isopen():
            self.proxy.reopen() 
        self.params.version = self.proxy.get_version()
        LF.params.version = self.params.version
        doc.proxies[self.proxy.get_path()] = self.proxy
        logging.debug('Effective version is now', repr(self.params.version))
        if not len(self.proxy.conf):
            logging.debug('Reloading proxy conf')
            self.proxy.load_conf()
        # Redefine LF.conf if empty
        if not LF.conf:
            logging.debug('Redefining LF.conf')
            conf = self.proxy.conf  # ConfigurationProxy
            LF.conf = conf
        else:
            logging.debug('Found LF.conf', LF.conf)
            conf = LF.conf
            self.proxy.conf = LF.conf
        conf.doc = doc
        conf.filename = self.params.filename
        instr = conf['runningInstrument']
        LF.instrument = instr
        self.instrument = instr
        self.instrobj = getattr(conf, instr)
        LF.instr = self.instrobj
        # get the prefix from the test title
        LF.title = self.instrobj.measure['name']
        self.measurename = LF.title
        self.LF = LF
        # Dynamically generate load rules
        if self.params.gen_rule_load:
            self._rule_load, self.rule_load = generate_rule_from_conf(clientconf.confdb,
                                                                      conf, self._rule_load)
        return True

    def get_time_sequence(self, instrobj):
        # Detect main time dataset
        elapsed0 = int(self.proxy.get_node_attr('/conf', 'elapsed'))
        elapsed = int(instrobj.measure['elapsed'])
        elapsed = max(elapsed, elapsed0)
        logging.debug('got elapsed', elapsed)
        # Create time dataset
        time_sequence = []
        if (self.prefix + 't') in self._doc.data:
            logging.debug('Document already have a time sequence for this prefix', 
                          self.prefix)
            ds = self._doc.data[self.prefix + 't']
            try:
                ds = units.convert(ds, 'second', return_copy=False)
            except:
                pass
            time_sequence = ds.data
        if len(time_sequence) == 0:
            time_sequence = np.linspace(0, elapsed - 1, elapsed)
        if len(time_sequence) == 0:
            return False
        return time_sequence

    def get_available_autoload(self):
        """Return the list of available node names and the list of nodes which should
        be loaded during this import operation."""
        # Will list only Array-type descending from /summary
        cached = ['/summary/' + el.split(':')[-1]
                  for el in self._doc.cache.keys()]
        header = self.proxy.header(['Array', 'FixedTimeArray'], '/summary') + cached
        autoload = []
        excluded = []
        logging.debug('got header', len(header))
        # Match rules
        for h in header[:]:
            do_exc = bool(self.rule_exc) and bool(self.rule_exc.search(h))
            do_inc = bool(self.rule_inc) and bool(self.rule_inc.search(h))
            do_load = bool(self.rule_load) and bool(self.rule_load.search(h))
            # Force exclusion?
            if do_exc:
                # Force inclusion?
                if not do_inc:
                    header.remove(h)
                    excluded.append(h)
                    continue
            # Force loading?
            if do_load or do_inc:
                if h.endswith('/T'):
                    autoload.insert(0, h)
                    header.remove(h)
                    header.insert(0, h)
                else:
                    autoload.append(h)

        logging.debug('got autoload', autoload)
        logging.debug('got excluded', len(excluded))
        logging.debug('got header clean', len(header))
        self.LF.header = header
        # available, loaded
        self.available = header
        # First import T dataset (needed for Event's local T calculation)
        if '/summary/kiln/T' in autoload:
            autoload.remove('/summary/kiln/T')
            autoload.insert(0, '/summary/kiln/T')
        self.autoload = autoload
        return self.available, self.autoload

    def create_samples(self):
        """Create Sample object and append them to the LinkedFile.samples list.
        Returns the reference sample"""
        refsmp = Sample(linked=self.LF)
        self.LF.samples.append(refsmp)
        # build a list of samples
        for idx in range(self.instrobj.measure['nSamples'] + 1):
            n = 'sample' + str(idx)
            if not self.instrobj.has_child(n):
                self.LF.samples.append(None)
                continue
            smp = getattr(self.instrobj, n)
            self.LF.samples.append(
                Sample(conf=smp, linked=self.LF, ref=False, idx=idx))
        logging.debug('build', idx + 1, 'samples', self.LF.samples)
        return refsmp

    def search_data(self, col):
        return  self._doc.get_cache(col) or self.outdatasets.get(col, False)

    def create_local_datasets(self, pcol, sub_time_sequence=False, time_sequence=False, dataset_names=[]):
        """Create subordered time and temperature datasets"""
        logging.debug('creating local datasets',  pcol)
        r = []
        best_t = get_best_x_for(pcol, self.LF.prefix, dataset_names, '_t')
        best_T = get_best_x_for(pcol, self.LF.prefix, dataset_names, '_T')
        # No local dataset was found (back to global t): need to define one
        if best_t == self.LF.prefix + 't':
            # Get time column from document or from cache
            # Search a t child
            vcol = pcol.split(sep)
            parent = '/'.join(vcol[:-1])
            subcol = pcol + '_t'
            subt = self.search_data(subcol)
            # Search a t sibling
            if subt is False:
                subt = self.search_data(parent + '_t')
            if subt:
                r.append(subt)
            elif (sub_time_sequence is not False):
                subvar = vcol[-1] + '_t'
                subt = create_dataset(self.proxy, sub_time_sequence, subcol,
                                      subvar, subvar, subvar,
                                      linked_file=self.LF, reference_sample=self.refsmp,
                                      rule_unit=self.rule_unit,
                                      unit='second')
                r.append(subt)
        
        if not r: # or best_T != self.LF.prefix + 'kiln/T':
            # Neither subT is possible, or local already defined
            logging.debug('No time sequence found for local dataset', pcol)
            return r
        sub_time_sequence = subt.data
        # Get existing, created or cached ds
        subcol = pcol + '_T'
        subT = self.search_data(subcol)
        # Search a sibiling
        if not subT:
            subT = self.search_data(parent + '_T')
        if subT:
            r.append(subT)
            return r
        if time_sequence is False:
            logging.debug('No main time sequence for local dataset', pcol)
            return r

        # Search in doc, in current outdatasets (kiln/T should be the first
        # dataset imported!) and in cache
        Tcol = self.prefix + 'kiln/T'
        T = self.search_data(Tcol)
        # No main temperature dataset found: cannot build subordered T
        if T is False:
            logging.error(
                'No temperature dataset found for local dataset', pcol)
            return r
        # Generate a new local T dataset from the time dataset 
        # and the best T found (usually, kiln/T)
        sub_temperature_sequence = memory_saving_interpolation(time_sequence, 
                                                               T.data, 
                                                               sub_time_sequence)
        subvar = vcol[-1] + '_T'
        subT = create_dataset(self.proxy, sub_temperature_sequence, subcol,
                              subvar, subvar, subvar,
                              linked_file=self.LF, reference_sample=self.refsmp,
                              unit=T.unit,
                              rule_unit=self.rule_unit)
        r.append(subT)
        return r

    def _dataset_import(self, p, col0, time_sequence, availds, names, error_map, sub_map):
        pcol, mcol, m_var, col = prefixed_column_name(col0, self.prefix)
        job(p + 1, label=col)
        # Set m_update
        if (m_var == 't') or (col0 in self.autoload):
            m_update = True
        else:
            m_update = False

        # Avoid overwriting
        if (not self.params.overwrite) or (not m_update):
            # completely skip processing if dataset is already in document
            if pcol in self._doc.data:
                return False
            if pcol in self._doc.available_data and not m_update:
                return False               
        
        # Try reading cached data
        ds = False
        data = []
        opt = {}
        if pcol in self._doc.cache:
            ds = self._doc.get_cache(pcol, load_data=m_update)
            data = ds.data
            opt = getattr(ds, 'm_opt', False)
            logging.debug('Got data from cache', pcol, len(data), opt)

        sub_time_sequence = False
        is_local = (col0[-2:] in ('_T', '_t'))
        is_error = pcol in error_map.values()
        if col == 't':
            attr = []
            type = 'Float'
            opt = option.ao(
                {}, 't', 'Float', 0, 'Event Time', unit='second')['t']
        else:
            if len(opt) == 0 and not is_local:
                obj,  name = self.proxy.conf.from_column(col)
                if obj and obj.has_key(name):
                    opt = obj.gete(name)
                else:
                    logging.error(
                        'Cannot map dataset to option', col, col0, pcol, mcol)
            if opt is None:
                logging.debug('Cannot retrieve option definition', col)
                return False
            attr = opt.get('attr', [])
            type = opt.get('type', 'Float')
            if attr in ['', 'None', None, False, 0]:
                attr = []
        if not m_update:
            # leave ds empty
            #logging.debug('Not loading:', col0, m_update)
            pass
        elif col == 't':
            data = units.Converter.convert('second', self.params.time_unit, time_sequence)
        elif ('Event' not in attr) and (type != 'Table') and (len(data) == 0) and not is_local and not is_error:
            logging.debug('Loading data', col0)
            data = interpolated(self.proxy, col0, time_sequence)
        elif len(data) == 0 and col0 in self.LF.header:
            # Get raw data and time_sequence
            logging.debug('Getting raw data', col0)
            data = read_data(self.proxy, col0).transpose()
            sub_time_sequence = data[0]
            data = data[1]
        # Create the dataset
        if ds is False and data is not False:
            ds = create_dataset(self.proxy,
                                data, pcol, col, col0, m_var, m_update, p,
                                linked_file=self.LF, reference_sample=self.refsmp,
                                rule_unit=self.rule_unit, 
                                opt = opt)
        if ds is False:
            logging.debug('No dataset created for', col0)
            return False
        # Count the dataset
        if len(ds.data) > 0:
            names.append(pcol)
            self.outdatasets[pcol] = ds
        else:
            availds[pcol] = ds
        # Remember error dataset relation
        if opt and opt.has_key('error'):
            error_map[pcol] = opt['error']

        # Remember sub time sequence for local ds creation
        if len(ds.data) > 0 and col != 't' and (('Event' in attr) or (type == 'Table')):
            sub_map[pcol] = (sub_time_sequence)

        return ds

    def doImport(self):
        """Import data.  Returns a list of datasets which were imported."""
        # Linked file
        logging.debug('OperationMisuraImport')
        if not self.get_file_proxy():
            logging.debug('EMPTY FILENAME')
            return []
        LF = self.LF

        # Set available curves on the LF
        jobs(2)
        self.get_available_autoload()
        
        # Emit the number of jobs
        jobs(len(self.autoload) + len(self.available))

        self.refsmp = self.create_samples()

        # Get time sequence
        time_sequence = self.get_time_sequence(self.instrobj)
        if time_sequence is False:
            logging.error('No time_sequence! Aborting.', 
                          self.instrobj.measure['elapsed'])
            return []

        availds = {}
        names = []
        error_map = {}  # Dataset :-> Error option name mapping
        # Collect datasets which might have locals (pcol : sub_time_sequence)
        sub_map0 = {}
        sub_map = {}  # Local dataset mapping: main :-> (locals, )

        # First import cycle
        logging.debug('PRIMARY IMPORT')
        if self.params.dryrun or (not self.params.rebuild):
            target = self.autoload
        else:
            target = ['t'] + self.available
        for p, col0 in enumerate(target):
            self._dataset_import(
                p, col0, time_sequence, availds, names, error_map, sub_map0)

        # Error import cycle
        p = 0
        logging.debug('ERROR DS IMPORT')
        for main_pcol, error_name in error_map.items():
            m = from_column(main_pcol)
            m.pop(-1)
            m.append(error_name)
            col0 = '/summary/' + '/'.join(m)
            ds_name = prefixed_column_name(col0, self.prefix)[0]
            
            if main_pcol in self.outdatasets:
                self.autoload.append(col0)
                logging.debug('Added to autoload', col0, self.autoload)
            else:
                logging.debug('Skip error dataset', main_pcol, self.outdatasets.keys())
                error_map.pop(main_pcol)
                continue
            ds = self._dataset_import(
                p, col0, time_sequence, availds, names, error_map, sub_map0)
            logging.debug('Error dataset', main_pcol, error_name, ds_name, ds)
            if ds is False:
                error_map.pop(main_pcol)
            else:
                error_map[main_pcol] = ds_name
            p += 1
        # Local datasets creation
        # Create sub-time dataset. Should be done after the import finishes!
        overall_dataset_names = set(
            self.outdatasets.keys() + self._doc.data.keys() + self._doc.cache.keys())
        logging.debug('SUBORDERED DS IMPORT')
        for pcol, sub_time_sequence in sub_map0.iteritems():
            subds = self.create_local_datasets(
                pcol, sub_time_sequence, time_sequence, dataset_names=overall_dataset_names)
            for sub in subds:
                names.append(sub.m_name)
                self.outdatasets[sub.m_name] = sub
            if subds:
                logging.debug('Local datasets', pcol, subds, sub_map)
                sub_map[pcol] = subds
                
        # Error association cycle
        logging.debug('ERROR ASSOCIATION')
        for main_name, error_name in error_map.iteritems():
            # Remove any subordered T,t dataset
            for sub_ds in sub_map.get(error_name, []):
                sub_name = sub_ds.m_name
                if sub_name in names:
                    names.remove(sub_name)
                if sub_name in self.outdatasets:
                    self.outdatasets.pop(sub_name)
                if sub_name in availds:
                    availds.pop(sub_name)
            # Place error data into "serr" array
            logging.debug('Assigning error dataset', main_name, error_name)
            if error_name in self.outdatasets:
                error_ds = self.outdatasets.pop(error_name)
                main_ds = self.outdatasets[main_name]
                main_ds.serr = error_ds.data
            else:
                logging.debug('No error dataset found', main_name, error_name)
            if error_name in availds:
                availds.pop(error_name)
            if error_name in names:
                names.remove(error_name)
        
        self.imported_names = names
        self._outdatasets = self.outdatasets
        if self.params.dryrun:
            # Do not actually import anything - just keep a reference
            self.outdatasets = {}
            done()
            return []
        # Detect ds which should be removed from availds because already
        # contained in imported names
        avail_set = set(self._doc.available_data.keys())
        names_set = set(names).union(set(self._doc.data.keys()))
        for dup in names_set.intersection(avail_set):
            self._doc.available_data.pop(dup)
        logging.debug('emitting done')
        done()
        logging.debug('imported names:', names)
        self._doc.available_data.update(availds)

        # Update linked file parameters
        hdf_names = filter(
            lambda name: name.startswith(self.prefix), names_set)
        hdf_names = map(
            lambda name: ("/" + name.lstrip(self.prefix) + "$"), hdf_names)
        LF.params.rule_load = '\n'.join(hdf_names)
        return names
