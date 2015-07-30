#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
import veusz.plugins as plugins
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


class RemoveGapsPlugin(plugins.DatasetPlugin):
    # tuple of strings to build position on menu
    menu = ('Filter', 'Remove Gaps')
    # internal name for reusing plugin later
    name = 'RemoveGaps'
    # string which appears in status bar
    description_short = 'Remove Gaps'

    description_full = ('Remove gaps from a dataset.')

    def __init__(self, input_dataset='', output_dataset=''):
        self.fields = [
            plugins.FieldDataset(
                'input_dataset', 'Input Dataset Name', default=input_dataset),
            plugins.FieldDataset(
                'output_dataset', 'Output dataset name', default=output_dataset),
            plugins.FieldInt(
                'gap_amplitutde', 'Minimum gap amplitude', default=5),
            plugins.FieldInt(
                'gap_start_index', 'Start Time(s) of region with gaps', default=0),
            plugins.FieldInt(
                'gap_end_index', 'End Time(s) of region with gaps', default=-1),
        ]

    def getDatasets(self, fields):
        self.output_dataset = plugins.Dataset1D(fields['output_dataset'])
        return [self.output_dataset]

    def updateDatasets(self, fields, helper):
        input_dataset = helper.getDataset(fields['input_dataset'])
        gap_amplitutde = fields['gap_amplitutde']
        gaps_start_index = fields['gap_start_index']
        gaps_end_index = fields['gap_end_index']
        cleaned_data = remove_gaps_from(input_dataset.data, gap_amplitutde, gaps_start_index, gaps_end_index)
        self.output_dataset.update(
            data=cleaned_data, serr=input_dataset.serr, perr=input_dataset.perr, nerr=input_dataset.nerr)
        return [self.output_dataset]

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(RemoveGapsPlugin)
