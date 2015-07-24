#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
import veusz.plugins as plugins
import numpy
from utils import smooth


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
            plugins.FieldDataset('input_dataset', 'Input Dataset Name', default = input_dataset),
            plugins.FieldDataset('output_dataset', 'Output dataset name', default = output_dataset),
        ]

    def getDatasets(self, fields):
        self.output_dataset = plugins.Dataset1D(fields['output_dataset'])

        return [self.output_dataset]

    def updateDatasets(self, fields, helper):
        input_dataset = helper.getDataset(fields['input_dataset'])
        data = numpy.array(input_dataset.data)
        self.output_dataset.update(data=data, serr=input_dataset.serr, perr=input_dataset.perr, nerr=input_dataset.nerr)
        return [self.output_dataset]

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(RemoveGapsPlugin)
