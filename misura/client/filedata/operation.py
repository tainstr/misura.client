#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Libreria per il plotting semplice durante l'acquisizione."""
from misura.canon.logger import Log as logging
from exceptions import BaseException
import numpy as np
from copy import deepcopy
import re
from scipy.interpolate import InterpolatedUnivariateSpline

import veusz.dataimport.base as base

from dataset import MisuraDataset, Sample
import linked
from proxy import getFileProxy

from entry import iterpath

from .. import iutils, live
from .. import clientconf

from .. import units

from PyQt4 import QtCore

from misura.client import _

sep = '/'


class EmptyDataset(BaseException):
    pass


def getUsedPrefixes(doc):
    p = {}
    for name, ds in doc.data.iteritems():
        lf = ds.linked
        if lf is None:
            logging.debug('%s %s', 'no linked file for ', name)
            continue
#       print 'found linked file',lf.filename,lf.prefix
        p[lf.filename] = lf
    logging.debug('%s %s %s', 'getUsedPrefixes', p, doc.data.keys())
    return p


def get_linked(doc, params):
    opf = getUsedPrefixes(doc)
    # Find if the filename already has a prefix
    lf = opf.get(params.filename, False)
    if lf is not False:
        return lf
    # Find a new non-conflicting prefix
    prefix = params.prefix
    used = [lf.prefix for lf in opf.values()]
    while prefix in used:
        base, n, pre = iutils.guessNextName(prefix[:-1])
        prefix = pre + ':'
    params.prefix = prefix
    LF = linked.LinkedMisuraFile(params)
    LF.prefix = prefix
    logging.debug('%s %s', 'get_linked', prefix)
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
        'version': None,  # means latest
        'reduce': False,
        'reducen': 1000,
        'time_interval': 2,  # interpolation interval for time coord
        'rule_exc': clientconf.rule_exc,
        'rule_inc': clientconf.rule_inc,
        'rule_load': clientconf.rule_load,
        'rule_unit': clientconf.rule_unit,
    })


def read_data(proxy, col):
    """Read `col` node from `proxy`"""
    data0 = np.array(proxy.col(col, (0, None)))
    # FIXME: now superfluous?
    data = data0.view(np.float64).reshape((len(data0), 2))
    return data


def not_interpolated(proxy, col, startt, endt):
    """Retrieve `col` from `proxy` and extend its time range from `startt` to `endt`"""
    logging.debug('%s %s %s %s', 'not interpolating col', col, startt, endt)
    # Take first point to get column start time
    zt = proxy.col(col, 0)
    if zt is None or len(zt) == 0:
        logging.debug('%s %s %s', 'Skipping column: no data', col, zt)
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
        d = s - startt

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


def interpolated(proxy, col, ztime_sequence):
    """Retrieve `col` from `proxy` and interpolate it around `ztime_sequence`"""
    tdata = not_interpolated(proxy, col, ztime_sequence[0], ztime_sequence[-1])
    if tdata is False:
        return False
    t, val = tdata[0], tdata[1]
    # Empty column
    if val is False or len(val) == 0:
        return val
    f = InterpolatedUnivariateSpline(t, val, k=1)
    r = f(ztime_sequence)
    return r


def tasks():
    return getattr(live.registry, 'tasks', False)


def jobs(n, pid="File import"):
    # FIXME: causes random crashes while opening microscope tests in compiled
    # win exe
    return
    t = tasks()
    if not t:
        return
    t.jobs(n, pid)


def job(n, pid="File import", label=''):
    # FIXME: causes random crashes while opening microscope tests in compiled
    # win exe
    return
    t = tasks()
    if not t:
        return
    t.job(n, pid, label)


def done(pid="File import"):
    # FIXME: causes random crashes while opening microscope tests in compiled
    # win exe
    return
    t = tasks()
    if not t:
        return
    t.done(pid)


class OperationMisuraImport(QtCore.QObject, base.OperationDataImportBase):

    """Import misura HDF File format. This operation is also a QObject so it can send signals to other objects."""
    descr = 'import misura hdf file'
    proxy = False
    rule_exc = False
    rule_inc = False
    rule_load = False
    _rule_load = False
    rule_unit = False

    def __init__(self, params):
        """Create an import operation on the filename. Update defines if keep old data or completely wipe it."""

        QtCore.QObject.__init__(self)
        base.OperationDataImportBase.__init__(self, params)

        self.linked = True
        self.filename = params.filename
        self.uid = params.uid

        self.rule_exc = False
        if len(params.rule_exc) > 0:
            r = params.rule_exc.replace('\n', '|')
            logging.debug('%s %s', 'Exclude rule', r)
            self.rule_exc = re.compile(r)
        self.rule_inc = False
        if len(params.rule_inc) > 0:
            r = params.rule_inc.replace('\n', '|')
            logging.debug('%s %s', 'Include rule', r)
            self.rule_inc = re.compile(r)
        self.rule_load = False
        if len(params.rule_load) > 0:
            r = params.rule_load.replace('\n', '|')
            self._rule_load = r
            logging.debug('%s %s', 'Load rule', r)
            self.rule_load = re.compile(r)
        self.rule_unit = clientconf.RulesTable(params.rule_unit)

    @classmethod
    def from_dataset_in_file(cls, dataset_name, linked_filename, uid=''):
        """Create an import operation from a `dataset_name` contained in `linked_filename`"""
        if ':' in dataset_name:
            dataset_name = dataset_name.split(':')[1]
        p = ImportParamsMisura(filename=linked_filename,
                               uid=uid,
                               rule_exc=' *',
                               rule_load='^(/summary/)?' + dataset_name + '$',
                               rule_unit=clientconf.confdb['rule_unit'])
        op = OperationMisuraImport(p)
        return op

    def do(self, document):
        """Override do() in order to get a reference to the document!"""
        self._doc = document
        base.OperationDataImportBase.do(self, document)

    def get_file_proxy(self):
        """Try to open a FileProxy and a LinkedFile from the parameters (filename and uid)"""
        doc = self._doc
        if self.uid:
            new = clientconf.confdb.resolve_uid(self.uid)
            if new:
                logging.debug(
                    'Opening by uid %s: %s instead of %s', self.uid, new, self.filename)
                self.filename = new[0]
            else:
                logging.debug('Impossible to resolve uid: %s', self.uid)
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
        jobs(3, 'Reading file')
        # open the file
        fp = getattr(doc, 'proxy', False)
        logging.debug('%s %s %s %s', 'FILENAME', self.filename, type(fp), fp)
        print 'FILENAME', self.filename, type(fp), fp, self.uid
        if fp is False or not fp.isopen():
            self.proxy = getFileProxy(self.filename)
        else:
            self.proxy = fp
        job(1, 'Reading file', 'Configuration')
        if not self.proxy.isopen():
            self.proxy.reopen()
        if self.proxy.conf is False:
            self.proxy.load_conf()

        # Load required version
        if self.params.version is not None:
            self.proxy.set_version(self.params.version)
        conf = self.proxy.conf  # ConfigurationProxy
        LF.conf = conf
        instr = conf['runningInstrument']
        LF.instrument = instr
        self.instrobj = getattr(conf, instr)
        LF.instr = self.instrobj
        # get the prefix from the test title
        LF.title = self.instrobj.measure['name']
        self.measurename = LF.title
        self.LF = LF
        return True

    def get_time_sequence(self, instrobj):
        # Detect main time dataset
        elapsed0 = self.proxy.get_node_attr('/conf', 'elapsed')
        elapsed = int(instrobj.measure['elapsed'])
        elapsed = max(elapsed, elapsed0)
        logging.debug('%s %s', 'got elapsed', elapsed)
        # Create time dataset
        time_sequence = []
        if self._doc.data.has_key(self.prefix + 't'):
            logging.debug(
                '%s %s', 'Document already have a time sequence for this prefix', self.prefix)
            ds = self._doc.data[self.prefix + 't']
            try:
                ds = units.convert(ds, 'second')
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
        header = self.proxy.header(['Array'], '/summary')
        autoload = []
        excluded = []
        logging.debug('%s %s', 'got header', len(header))
        # Match rules
        for h in header[:]:
            exc = False
            if self.rule_exc and self.rule_exc.search(h) is not None:
                # Force inclusion?
                if (not self.rule_inc) or (self.rule_inc.search(h) is None):
                    exc = True
            # Force loading?
            if self.rule_load and self.rule_load.search(h) is not None:
                autoload.append(h)
                exc = False
            # Really exclude (no load, no placeholder)
            if exc:
                header.remove(h)
                excluded.append(h)
        logging.debug('%s %s', 'got autoload', autoload)
        logging.debug('%s %s', 'got excluded', len(excluded))
        logging.debug('%s %s', 'got header clean', len(header))
        self.LF.header = header
        # available, loaded
        self.available = header
        self.autoload = autoload
        return self.available, self.autoload

    def create_samples(self):
        """Create Sample object and append them to the LinkedFile.samples list.
        Returns the reference sample"""
        refsmp = Sample(linked=self.LF)
        self.LF.samples.append(refsmp)
        # build a list of samples
        for idx in range(self.instrobj.measure['nSamples']):
            smp = getattr(self.instrobj, 'sample' + str(idx), False)
            if not smp:
                break
            self.LF.samples.append(
                Sample(conf=smp, linked=self.LF, ref=False, idx=idx))
        logging.debug(
            '%s %s %s %s', 'build', idx + 1, 'samples', self.LF.samples)
        return refsmp

    def assign_sample_to_dataset(self, ds):
        """Find out the sample index to which this dataset refers"""
        col = ds.m_col
        var, idx = iutils.namingConvention(col)
        if '/sample' in col:
            parts = col.split(sep)
            for q in parts:
                if q.startswith('sample'):
                    break
            i = int(q[6:]) + 1
            smp = self.LF.samples[i]
            logging.debug(
                '%s %s %s %s %s %s', 'Assigning sample', i, 'to curve', col, smp, smp.ref)
            ds.m_smp = smp
            ds.m_var = var
            # Retrieve initial dimension from sample
            if var == 'd' and smp.conf.has_key('initialDimension'):
                ds.m_initialDimension = smp.conf['initialDimension']

        if ds.m_smp is False:
            ds.m_smp = self.refsmp
            return False
        return True

    def assign_label(self, ds, col0):
        """Assigns an m_label to the dataset"""
        if col0 != 't':
            ds_object, ds_name = ds.m_conf.from_column(col0)
            opt = ds_object.gete(ds_name)
            ds.m_label = _(opt["name"])
            if opt.has_key('csunit'):
                ds.old_unit = opt["csunit"]
        else:
            ds.m_label = _("Time")

    def assign_node_attributes(self, ds):
        """Try to read column metadata from node attrs"""
        for meta in ['percent', 'initialDimension']:
            val = 0
            if self.proxy.has_node_attr(ds.m_col, meta):
                val = self.proxy.get_node_attr(ds.m_col, meta)
                if type(val) == type([]):
                    val = 0
            setattr(ds, 'm_' + meta, val)

    def create_dataset(self, data, pcol, col, col0, m_var, m_update=True, p=0):
        # Get meas. unit
        u = 'None'
        if col == 't':
            u = 'second'
        else:
            u = self.proxy.get_node_attr(col, 'unit')
            if u in ['', 'None', None, False, 0]:
                u = False
            # Correct missing celsius indication
            if not u and m_var == 'T':
                u = 'celsius'
        logging.debug('%s', 'building the dataset')
        ds = MisuraDataset(data=data, linked=self.LF)
        ds.m_name = pcol
        ds.m_pos = p
        ds.m_smp = self.refsmp
        ds.m_var = m_var
        ds.m_col = col
        ds.m_update = m_update
        ds.m_conf = self.proxy.conf
        ds.unit = str(u) if u else u
        ds.old_unit = ds.unit

        # Automatic unit conversion
        if len(data) > 0 and col != 't':
            # Units conversion
            nu = self.rule_unit(col)
            if u and nu:
                ds = units.convert(ds, nu[0])

        # Add the hierarchy tags
        for sub, parent, leaf in iterpath(pcol):
            if leaf:
                ds.tags.add(parent)

        self.assign_sample_to_dataset(ds)

        self.assign_label(ds, col0)
        if len(data) > 0 and col != 't':
            self.assign_node_attributes(ds)

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
        job(2, 'Reading file', 'Header')
        available, autoload = self.get_available_autoload()

        # Emit the number of jobs
        jobs(len(autoload))

        self.refsmp = self.create_samples()

        # Get time sequence
        time_sequence = self.get_time_sequence(self.instrobj)
        if time_sequence is False:
            logging.debug(
                '%s %s', 'No time_sequence! Aborting.', self.instrobj.measure['elapsed'])
            return []

        outds = {}
        availds = {}
        names = []
        for p, col0 in enumerate(['t'] + available):
            col = col0.replace('/summary/', '/')
            mcol = col
            if mcol.startswith(sep):
                mcol = mcol[1:]
            if mcol.endswith(sep):
                mcol = mcol[:-1]
            pcol = self.prefix + mcol
            m_var = col.split('/')[-1]
            # Set m_update
            if m_var == 't' or col0 in self.autoload:
                m_update = True
            else:
                m_update = False

            sub_time_sequence = False
            attr = self.proxy.get_node_attr(col, 'attr')
            if attr in ['', 'None', None, False, 0]:
                attr = []

            # Read data
            if not m_update:
                # completely skip processing if dataset is already in document
                if self._doc.data.has_key(pcol):
                    return False
                # data is not loaded anyway
                data = []
            elif col == 't':
                data = time_sequence
            elif 'Event' not in attr:
                data = interpolated(self.proxy, col0, time_sequence)
                # Interpolation error
                if data is False:
                    data = []
            else:
                # Get raw data and time_sequence
                data = read_data(self.proxy, col).transpose()
                sub_time_sequence = data[0]
                data = data[1]

            # Create the dataset
            ds = self.create_dataset(
                data, pcol, col, col0, m_var, m_update, p)
            if ds is False:
                continue

            # Count the dataset
#           LF.children.append(pcol) #???
            if len(ds.data) > 0:
                names.append(pcol)
                outds[pcol] = ds
            else:
                availds[pcol] = ds
                
            # Create sub-time dataset
            if sub_time_sequence is not False:
                subcol = pcol+sep+'t'
                subvar = 't'
                subds = self.create_dataset(sub_time_sequence, subcol,
                                            subvar, subvar, subvar)
                names.append(subcol)
                outds[subcol] = subds
                
            
            
            job(p + 1)

        # Detect ds which should be removed from availds because already
        # contained in imported names
        avail_set = set(self._doc.available_data.keys())
        names_set = set(names).union(set(self._doc.data.keys()))
        for dup in names_set.intersection(avail_set):
            self._doc.available_data.pop(dup)
        logging.debug('%s', 'emitting done')
        done()
        done('Reading file')
        logging.debug('%s %s', 'imported names:', names)
        self._doc.available_data.update(availds)
        self.outdatasets = outds

        LF.params.rule_load = '\n'.join(map(lambda name: "/" + name + "$",
                                            names_set)).replace('0:', '')

        return names
