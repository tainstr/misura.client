#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import numpy
from utils import smooth


def remove_gaps_from(all_data, threshold, start_index=0, end_index=None):
    if end_index == -1:
        end_index = None

    clean_data = numpy.copy(all_data)
    data_with_gaps = clean_data[start_index:end_index]
    diffs = numpy.diff(data_with_gaps)
    gaps_indexes = numpy.where(numpy.abs(diffs) > threshold)[0]

    for gap_index in gaps_indexes:
        for i in range(gap_index + 1 + start_index, len(clean_data)):
            clean_data[i] = clean_data[i] - diffs[gap_index]

    return clean_data


