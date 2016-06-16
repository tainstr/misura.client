#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Automated option->dataset generation utilities"""
import numpy as np
from copy import copy

import veusz.plugins as plugins
import veusz.document as document


from .. import _

possible_timecol_names = set(['Time', 'time', 't'])
possible_Tcol_names = set(['Temp.', 'Temp', 'Temperature',
                           'T', 'temp', 'temp.', 'temperature'])
possible_value_names = set(['Value','value','val','v'])

def new_dataset_operation(original_dataset, data, name, label, path, unit='volt'):
    """Create a new dataset by copying `original_dataset` and overwriting with `data`.
    Returns an operation to be executed by the document."""
    old_unit = getattr(original_dataset, 'old_unit', unit)
    new_dataset = copy(original_dataset)
    new_dataset.tags = set([])
    new_dataset.data = plugins.numpyCopyOrNone(data)
    new_dataset.m_var = name
    new_dataset.m_pos = 2
    new_dataset.m_name = new_dataset.m_var
    new_dataset.m_col = new_dataset.m_var
    new_dataset.old_unit = old_unit
    new_dataset.unit = unit
    new_dataset.m_percent = False
    new_dataset.m_label = _(label)
    prefix = original_dataset.linked.prefix
    if not path.startswith(prefix):
        path = prefix+path.lstrip('/')
    return document.OperationDatasetSet(path, new_dataset)

def search_column_name(column_names_list, possible_names):
    """Search for `column_names` amonst `possible_names` and return its index"""
    column_names = set(column_names_list)
    missing = possible_names - column_names
    col_name = possible_names - missing
    if len(col_name) != 1:
        print 'No univoque col name', missing, col_name, possible_names
        return False, -1
    col_name = col_name.pop()
    idx = column_names_list.index(col_name)
    return col_name, idx

def add_datasets_to_doc(datasets, doc, original_dataset=False):
    """Create proper Veusz datasets and include in doc via operations"""
    unit = False
    ops = []
    #TODO: find a way to reliably detect the original_dataset for multi-test docs!
    if not original_dataset:
        original_dataset = doc.data['0:t']
    for (pure_dataset_name, (data, variable_name, label)) in datasets.iteritems():
        op = new_dataset_operation(original_dataset, data, variable_name, label, pure_dataset_name, unit=unit)
        ops.append(op)
    if len(ops) > 0:
        doc.applyOperation(
                document.OperationMultiple(ops, descr='Add new datasets'))    
    return len(ops)
    
def table_to_datasets(proxy, opt, doc):
    """Generate time, temp, etc datasets from Table-type `opt`."""
    tab = opt['current']
    header = tab[0]
    # Invalid table
    if len(header) == 0:
        return False
    print 'table_to_datasets', proxy['fullpath'], opt['handle'], header
    column_types = [e[1] for e in header]
    s = set(column_types)
    if len(s) > 1 or s.pop() != 'Float':
        print 'Skipping table header for non-Floats', s
        return False
    # Search for time/temp columns
    column_names = [e[0] for e in header]
        
    
    timecol_name, timecol_idx = search_column_name(column_names, 
                                                   possible_timecol_names)

    Tcol_name, Tcol_idx = search_column_name(column_names, 
                                             possible_Tcol_names)
    
    if (timecol_name == False) and (Tcol_name == False):
        print 'Neither time nor temperature columns were found', header
        return False
    
    
    base_path = proxy['fullpath']+opt['handle']
    datasets = {}
    tab = np.array(tab[1:]).transpose()
    if len(tab) == 0:
        print 'Skip empty table'
        return False
    
    value_idxes = range(len(tab))
    if timecol_idx in value_idxes:
        value_idxes.remove(timecol_idx)
    if Tcol_idx in value_idxes:
        value_idxes.remove(Tcol_idx)
        
    if len(value_idxes)==0:
        print 'No value columns found in table', len(tab), tab, value_idxes, header
        return False
    
    def add_tT(path):
        if timecol_name:
            datasets[path+'/t'] = (tab[timecol_idx], 't', 'Time')
        if Tcol_name:
            datasets[path+'/T'] = (tab[Tcol_idx], 'T', 'Temperature')        
    
    if len(value_idxes)==1:
        idx = value_idxes[0]
        datasets[base_path] = (tab[idx], opt['handle'], opt['name'])
        add_tT(base_path)
    else:
        for idx in value_idxes:
            name = column_names[idx]
            sub_path = base_path+'/'+ name
            datasets[sub_path] = (tab[idx], name, opt['name']+' - '+name)
        add_tT(base_path)
            
    add_datasets_to_doc(datasets, doc)
    return True

def generate_datasets(proxy, doc):
    """Generate all datasets from proxy's options"""
    for key, opt in proxy.describe().iteritems():
        if opt['type'] == 'Table':
            table_to_datasets(proxy, opt, doc)


def recurse_generate_datasets(base_proxy, doc):
    """Generates all datasets for proxy and recursively downward 
    to the portion of tree stemming from proxy."""
    generate_datasets(base_proxy, doc)
    for proxy in base_proxy.devices:
        recurse_generate_datasets(proxy, doc)
