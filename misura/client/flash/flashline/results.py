#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Parse useful results.* files"""
import numpy as np
import os

# Seg Temp   t1/2   Parker  Koski  Heckman  Cowan 5 Cowan 10 C&T R1 C&T R2
# C&T R3 Degiovanni 2/3 1/2 1/3
cols_all = {'segment': 0,
            'T': 1,
            'halftime': 2,
            'parker': 3,
            'koski': 4,
            'cowan5': 5,
            'cowan10': 6,
            'clark_taylor1': 7,
            'clark_taylor2': 8,
            'clark_taylor3': 9,
            'degiovanni': 10,
            '2/3': 11,
            '1/2': 12,
            '1/3': 13,
            'equilibrium':14} # Bool: 1 ok, 0 quasi

def read_from_label(filename, label):
    dat = open(filename, 'r').read()
    # Search column header
    i = dat.find(label)
    # Split data lines
    dat = dat[i:].splitlines()[2:]
    # Clean empty lines
    dat = filter(lambda v: len(v)>2, dat)  
    return dat

def process_line(line, temperature_column = 0):
    """Removes empty cells; detects quasi-equilibrium temps and appends last column"""
    line = line[:-2].split(' ')
    line = filter(lambda v: v!='', line)
    if 'Q' in line[temperature_column]: 
        line[temperature_column] = line[temperature_column].replace('Q','')
        line.append(0)
    else:
        line.append(1)
    return line

def all_table(filename):
    """Parse a *.all results file. 
    Returns a transposed table (tab[col][row])"""
    if not os.path.exists(filename):
        return None
    dat = read_from_label(filename, 'Seg Temp   t1/2')
    current_segment = None
    table = []
    for line in dat:
        # Change segment
        segment = line[:3].replace(' ', '')
        if segment:
            current_segment = int(segment)
        if current_segment is None:
            continue
        line = process_line(line[3:], temperature_column=0)
        # Insert segment number, zero-based
        line.insert(0, current_segment-1)
        table.append(line)
        
    table = np.array(table)
    return table 

def segment_temperature_values(filename):
    """Parse a generic results file containing three columns for segment, temperature,
    average and one additional column per shot/value. 
    Returns table[row][col]
    Supported: *.clt, *.deg, *.cow, *.hft, *.gdf"""
    dat = read_from_label(filename, 'Segment Temperature')
    table = []
    for line in dat:
        line = process_line(line, temperature_column=1)
        table.append(line)
    
    return np.array(table)

  
        