#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

def get_best_x_for(y_path, prefix, data, page):
    if page.startswith('/time'):
        xname = prefix + 't'
    else:
        sample_temperature_path = get_temperature_of_sample_with_path(y_path)
        if sample_temperature_path in data:
            xname = sample_temperature_path
        else:
            xname = prefix + 'kiln/T'

    return xname

def get_temperature_of_sample_with_path(sample_path):
    return "/".join(sample_path.split("/")[0:-1]) + "/T"

def is_temperature(path):
    return re.search('.*/T$|.*kiln/T', path)

def kiln_temperature_for(path):
    return path.split(':')[0] + ":kiln/T"