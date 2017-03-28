#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Automated option->dataset generation utilities"""
import numpy as np
from copy import copy
import re

from misura.canon import option
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import veusz.document as document


from .. import _

contains = lambda s, words: sum([word in s for word in words])

possible_timecol_names = ('time', )
is_time_col = lambda col: contains(col.lower(), possible_timecol_names)

possible_Tcol_names = ('temp', 'temp.', 'temperature', 'setpoint', )

is_T_col = lambda col: contains(col.lower(), possible_Tcol_names)

possible_error_names = ('error', 'err', 'uncertainty')

is_error_col = lambda col: contains(col.lower(), possible_error_names)



def new_dataset_operation(original_dataset, data, name, label, path, unit='volt', opt=False, error=None):
    """Create a new dataset by copying `original_dataset` and overwriting with `data`.
    Returns an operation to be executed by the document."""
    old_unit = unit
    if opt:
        if unit is False:
            unit = opt.get('csunit', False)
        old_unit = opt.get('unit', unit)
    old_unit = getattr(original_dataset, 'old_unit', old_unit)
    if not opt:
        opt = original_dataset.m_opt
    new_dataset = copy(original_dataset)
    new_dataset.attr = dict({}, **original_dataset.attr)
    new_dataset.tags = set([])
    new_dataset.data = plugins.numpyCopyOrNone(data)
    new_dataset.m_opt = opt
    new_dataset.m_var = name
    new_dataset.m_pos = 2
    new_dataset.m_col = new_dataset.m_var
    new_dataset.old_unit = old_unit
    new_dataset.unit = unit
    new_dataset.m_label = _(label)
    
    prefix = original_dataset.linked.prefix
    if not path.startswith(prefix):
        path = prefix + path.lstrip('/')
    new_dataset.m_name = path
    if error is not None:
        new_dataset.serr = error
    return document.OperationDatasetSet(path, new_dataset)


def search_column_name(column_names_list, is_col=lambda col: False):
    """Search for `column_names_list` checking with is_col() function"""
    idx = -1
    col_name = False
    for i, col in enumerate(column_names_list):
        if is_col(col):
            if col_name:
                logging.debug('No univoque col name', col_name)
                return False, -1
            logging.debug('Found', col, i)
            col_name = col
            idx = i
    return col_name, idx


def add_datasets_to_doc(datasets, doc, original_dataset=False):
    """Create proper Veusz datasets and include in doc via operations"""
    unit = False
    ops = []
    # TODO: find a way to reliably detect the original_dataset for multi-test
    # docs!
    if not original_dataset:
        original_dataset = doc.data['0:t']
    for (pure_dataset_name, values) in datasets.iteritems():
        (data, variable_name, label, error, opt) = values[:5]
        op = new_dataset_operation(original_dataset, data, variable_name, label, pure_dataset_name,
                                   unit=unit, error=error, opt=opt)
        ops.append(op)

    if len(ops) > 0:
        doc.applyOperation(
            document.OperationMultiple(ops, descr='Add new datasets'))
    return len(ops)


def table_to_datasets(proxy, opt, doc):
    """Generate time, temp, etc datasets from Table-type `opt`."""
    tab = opt['current']
    header = tab[0]
    Ncol = len(header)
    unit = opt.get('unit', False)
    if not unit:
        unit = [False] * Ncol
    # Invalid table
    if Ncol == 0:
        return False
    logging.debug(
        'table_to_datasets', proxy['fullpath'], opt['handle'], header)
    column_types = [e[1] for e in header]
    s = set(column_types)
    if len(s) > 1 or s.pop() != 'Float':
        print 'Skipping table header for non-Floats', s
        return False
    # Search for time/temp columns
    column_names = [e[0] for e in header]

    timecol_name, timecol_idx = search_column_name(column_names,
                                                   is_time_col)

    Tcol_name, Tcol_idx = search_column_name(column_names,
                                             is_T_col)
    Ecol_name, Ecol_idx = search_column_name(column_names,
                                             is_error_col)

    if (timecol_name == False) and (Tcol_name == False):
        logging.debug(
            'Neither time nor temperature columns were found', header)
        return False
    handle = opt['handle']
    base_path = proxy['fullpath'] + handle
    datasets = {}
    tab = np.array(tab[1:]).transpose()
    if len(tab) == 0:
        logging.debug('Skip empty table')
        return False
    value_idxes = range(tab.shape[0])
    if timecol_idx in value_idxes:
        value_idxes.remove(timecol_idx)
    if Tcol_idx in value_idxes:
        value_idxes.remove(Tcol_idx)
    if Ecol_idx in value_idxes:
        value_idxes.remove(Ecol_idx)

    if len(value_idxes) == 0:
        logging.debug(
            'No value columns found in table', len(tab), tab, value_idxes, header)
        return False

    def add_tT(path):
        if timecol_name:
            u = unit[timecol_idx]
            if not u:
                u = 'second'
            topt = option.ao({}, handle+'_t', 'Float', 0, 'Time', unit=u).popitem()[1]
            datasets[
                path + '_t'] = (tab[timecol_idx], path + '_t', 'Time', None, topt)
        if Tcol_name:
            u = unit[Tcol_idx]
            if not u:
                u = 'celsius'
            Topt = option.ao({}, handle+'_T', 'Float', 0, 'Temperature', unit=u).popitem()[1]
            datasets[
                path + '_T'] = (tab[Tcol_idx], path + '_T', 'Temperature', None, Topt)

    if len(value_idxes) == 1:
        idx = value_idxes[0]
        err = None
        if Ecol_name:
            err = tab[Ecol_idx]
        datasets[base_path] = (tab[idx], opt['handle'], opt['name'], err, opt)
        add_tT(base_path)
    else:
        logging.debug('Generating multi column datasets')
        for idx in value_idxes:
            name = column_names[idx]
            sub_path = base_path + '/' + name
            datasets[sub_path] = (tab[idx], name, opt['name'] + ' - ' + name, 
                                  None, opt)
        add_tT(base_path)
    add_datasets_to_doc(datasets, doc)
    return True


def generate_datasets(proxy, doc, rule=False):
    """Generate all datasets from proxy's options"""
    if rule:
        rule = re.compile(rule)
    for key, opt in proxy.describe().iteritems():
        if rule and not rule.search(key):
            continue
        if opt['type'] == 'Table':
            table_to_datasets(proxy, opt, doc)


def recurse_generate_datasets(base_proxy, doc, rule=False):
    """Generates all datasets for proxy and recursively downward 
    to the portion of tree stemming from proxy."""
    generate_datasets(base_proxy, doc, rule=rule)
    for proxy in base_proxy.devices:
        recurse_generate_datasets(proxy, doc, rule=rule)
