#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

def get_best_x_for(y_path, prefix, data, page):
    # Default x datasets:
    if page.startswith('/time'):
        target = 't'
        xname = prefix + 't'
    else:
        target = 'T'
        xname = prefix + 'kiln/T'
    # Possible nearby  datasets: 
    subordered_x = get_suborderd_x(y_path, name=target)
    neighbor_x = get_neighbor_x(y_path, name=target)
    print 'get_best_x_for', y_path, prefix, target, subordered_x, neighbor_x
    # Subordered has precedence
    if subordered_x in data:
        xname = subordered_x
    # Then neighbor
    elif neighbor_x in data:
        xname = neighbor_x
    # Then default
    return xname

def get_suborderd_x(dataset_path, name='T'):
    return dataset_path + "/" + name

def get_neighbor_x(dataset_path, name='T'):
    return "/".join(dataset_path.split("/")[0:-1]) + "/" + name

def is_temperature(path):
    return re.search('.*/T$|.*kiln/T', path)

def kiln_temperature_for(path):
    return path.split(':')[0] + ":kiln/T"

def is_calibratable(path):
    return re.search('horizontal/.*sample0/d$|vertical/.*sample0/d$', path)