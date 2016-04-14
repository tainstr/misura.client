#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Custom Misura plotting facilities."""
import re

import veusz.plugins as plugins
import veusz.document as document
from misura.client import iutils
from misura.canon.logger import Log as logging
from .. import axis_selection
from PlotPlugin import PlotDatasetPlugin


class DefaultPlotPlugin(plugins.ToolsPlugin):

    """Default Plot from a list of Misura datasets."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Make a default plot from a list of datasets')
    # unique name for plugin
    name = 'Misura default plot'
    # name to appear on status tool bar
    description_short = 'Default plot for Misura datasets'
    # text to appear in dialog box
    description_full = 'Default plot for Misura datasets'

    def __init__(self, dsn=[], rule=''):
        """Make list of fields."""

        self.fields = [
            plugins.FieldDatasetMulti("dsn", 'Dataset names'),
            plugins.FieldText("rule", 'Plotting rule', default=rule)
        ]

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.doc = cmd.document
        dsn = fields['dsn']
        vars = []
        rp = fields['rule'].replace('\n', '|')
        if len(rp) > 0:
            rp = re.compile(rp)
        else:
            rp = False
        for ds in dsn:
            ds1 = ds
            if ':' in ds1:
                ds1 = ds1.split(':')[1]
            var = iutils.namingConvention(ds1)[0]
            logging.debug('%s %s %s', 'Checking', ds, var)
            if rp and rp.search(ds1):
                vars.append(ds)

        vars = sorted(vars)
        logging.debug('%s %s', "VARS", vars)
        xt = []
        xT = []
        yt = []
        yT = []
        for ds in vars:
            prefix = ''
            if ':' in ds:
                prefix, ds1 = ds.split(':')
                prefix += ':'
            timeds = axis_selection.get_best_x_for(
                ds, prefix, self.doc.data, '/time/time')
            if timeds:
                yt.append(ds)
                xt.append(timeds)
            else:
                print 'NO TIMEDS FOUND FOR', ds

            if not axis_selection.is_temperature(ds):
                ds_temperature = axis_selection.get_best_x_for(
                    ds, prefix, self.doc.data, '/temperature/temp')
                if ds_temperature:
                    xT.append(ds_temperature)
                    yT.append(ds)

        result = PlotDatasetPlugin().apply(
            cmd, {'x': xt, 'y': yt, 'currentwidget': '/time/time'})
        result.update(PlotDatasetPlugin().apply(
            cmd, {'x': xT, 'y': yT, 'currentwidget': '/temperature/temp'}))
        return result
