#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Automated option->dataset generation utilities"""
import numpy as np
import veusz.plugins as plugins
import veusz.document as document


possible_timecol_names = set(['Time', 'time', 't'])
possible_Tcol_names = set(['Temp.', 'Temp', 'Temperature',
                           'T', 'temp', 'temp.', 'temperature'])
possible_value_names = set(['Value','value','val','v'])

def search_column_name(column_names_list, possible_names):
    """Search for `column_names` amonst `possible_names` and return its index"""
    column_names = set(column_names_list)
    missing = possible_timecol_names - column_names
    col_name = possible_names - missing
    if len(col_name) != 1:
        print 'No univoque col name', col_name, possible_names
        return False, -1
    col_name = col_name[0]
    idx = column_names_list.index(col_name)
    return col_name, idx


def add_dataset_to_doc(datasets, doc):
    return False

def table_to_datasets(proxy, opt, doc):
    """Generate time, temp, etc datasets from Table-type `opt`."""
    tab = opt['current']
    header = tab[0]
    # Invalid table
    if len(header) == 0:
        return False
    print 'table_to_datasets', proxy['fullpath'], opt['handle'], header
    column_types = [e[1] for e in header]
    s = len(set(column_types))
    if len(s) > 0 or s[0] != 'Float':
        print 'Skipping table header for non-Floats', s
        return False
    # Search for time/temp columns
    timecol = None
    Tcol = None
    vcol = None
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
    
    value_cols = {}
    value_idxes = range(len(tab))
    if timecol_idx in value_idxes:
        value_idxes.remove(timecol_idx)
    if Tcol_idx in value_idxes:
        value_idxes.remove(Tcol_idx)
        
    if len(value_idxes)==0:
        print 'No value columns found in table', header
        return False
    
    def add_tT(path):
        if timecol_name:
            datasets[path+'/t'] = tab[timecol_idx]
        if Tcol_name:
            datasets[path+'/T'] = tab[Tcol_idx]        
    
    if len(value_idxes)==1:
        datasets[base_path] = tab[value_idxes[0]]
        add_tT(base_path)
    else:
        for idx in value_idxes:
            sub_path = base_path+'/'+column_names[idx]
            datasets[sub_path] = tab[idx]
            add_tT(sub_path)
    ops = []
    for name, data in datasets.iteritems():
        op = add_dataset_to_doc(name, data, doc)
        if op:
            ops.add(op)
    if len(ops) > 0:
        doc.applyOperation(
            document.OperationMultiple(ops, descr='Generate datasets from tables'))       
    return True




def generate_datasets(proxy, doc):
    """Generate all datasets from proxy's options"""
    for key, opt in proxy.describe().iteritems():
        if opt['type'] == 'Table':
            table_to_datasets(proxy, opt, doc)


def recurse_generate_datasets(proxy, doc):
    """Generates all datasets for proxy and recursively downward 
    to the portion of tree stemming from proxy."""
    generate_datasets(proxy, doc)
    for obj in proxy.devices:
        recurse_generate_datasets(obj, doc)
