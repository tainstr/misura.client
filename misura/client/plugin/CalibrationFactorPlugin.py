#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Get calibration factor from standard expansion curve"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from copy import copy
import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline

import veusz.plugins as plugins
import veusz.document as document
import utils
from misura.client import _, units

from misura.canon.csutil import find_nearest_val

# name: (T, %dL/L20°C)
standards = {
    # https://www-s.nist.gov/srmors/view_cert.cfm?srm=738
    'NIST-SRM738': (	np.array([20,  27,  67, 107, 147, 187, 227, 267, 307, 347, 387, 427, 467, 507]),
                     np.array([0,  69, 466, 872, 1288, 1714, 2149, 2593,
                               3048, 3511, 3984, 4467, 4959, 5461]) * 10**-4
                     ),
    # http://www.ceramics.nist.gov/srd/summary/scdaos.htm
    'Al2O3': (
        np.array([	0,		20,		500,   1000,  1200,	  1400,	  1500]),
        np.array(
                    [0.,     92.,   3550., 8100., 9960., 11900., 12900.]) * 10**-4,
    ),
    # http://www.ceramics.nist.gov/srd/scd/Z00665.htm
    'Al2O3-Dil': (np.array([0,  27,     77,     127,    177,     227,     277,     327,     377,     427,     477,     527,  
                            627,      727,    827,     927,     1027,    1127,    1227,     1327,     1427,    1527,     1627,     1727]),
                  np.array([0., 150.93, 442.75, 767.08, 1116.87, 1484.58, 1869.75, 2266.11, 2672.93, 3087.21, 3510.72, 3941.96,
                            4809.09, 5699.68, 6591.19, 7490.16, 8390.59, 9297.75, 10208.64, 11120.26, 12043.88, 12964.23, 13878.31, 14800.39]) * 10**-4,
                  ),
    # http://www.ceramics.nist.gov/srd/scd/Z00662.htm
    'Al2O3-N-Diffraction': (
        np.array([20, 	100,		200, 	300,  400,  500,  600,  700,  800,  900,  1000,
                  1100,  1200,  1300,  1400,  1500,  1600,  1700,  1800,  1900,  2000,  2050]),
        np.array([0.,    756.6,   1540.8,   2343.6,   3165.6,   4012.,	4806.,   5732.3,   6624.8,   7535.7,   8468.,   9408.3,
                  10368.,  11349.,  12335.4,  13360.5,  14387.2,  15436.,	16507.8,  17584.5,  18696.,  19247.45]) * 10**-4
    ),
    # Calibration certificate RU 01 N.2416-681-03566
    #FIXME: WRONG DATA!!!!
    'Sapphire': (
        np.array([0,    50,   100,  150,  200,  250,  300,  350,  400,  450,  500,  550,  600,  650,  700,  750,
                  800,  850,  900,  950,  1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400, 1450, 1500]),
        np.array([511., 552., 586., 615., 639., 661., 681., 698., 713., 726., 738., 749., 759., 768., 777., 786.,
                  794., 802., 810., 817., 825., 832., 839., 846., 854., 861., 867., 874., 881., 888., 895.]) * 10**-4
    ),
    # DE Data table
    'Platinum': (
        np.array([20, 500,   1000,   1200,   1400,  1500]),
        np.array([0., 4642., 10104., 12549., 15169, 16563, ]) * 10**-4,
    ),             
}


class CalibrationFactorPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Dilatometry calibration factor calculation"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', _('Calibration factor'))
    # unique name for plugin
    name = 'Calibration Factor'
    # name to appear on status tool bar
    description_short = _('Dilatometry calibration factor')
    # text to appear in dialog box
    description_full = _(
        'Get calibration factor from standard expansion curve')
    preserve = True

    def __init__(self, d='', T='', std='NIST-SRM738', start=50, end=50, label=True, add=True):
        """Make list of fields."""

        self.fields = [
            plugins.FieldDataset("d", descr=_("Expansion dataset"), default=d),
            plugins.FieldDataset(
                "T", descr=_("Temperature dataset"), default=T),
            plugins.FieldCombo(
                "std", descr=_("Calibraiton Standard"), items=standards.keys(), default=std),
            plugins.FieldFloat(
                'start', descr=_('First temperature margin'), default=start),
            plugins.FieldFloat(
                'end', descr=_('Last temperature margin'), default=end),
            plugins.FieldBool(
                'label', _('Draw calibration label'), default=label),
            plugins.FieldBool(
                'add', _('Add calibration datasets'), default=add),
        ]

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.doc = cmd.document

        ds = self.doc.data[fields['d']]
        Ts = self.doc.data[fields['T']]
        # Convert to percent, if possible
        self.inidim = getattr(ds, 'm_initialDimension', False)
        if not getattr(ds, 'm_percent', False):
            if self.inidim:
                ds = units.percent_conversion(ds, 'To Percent', auto=False)
        T = Ts.data
        # Cut away any cooling
        while max(T) != T[-1]:
            i = np.where(T == max(T))[0]
            T = T[:i]
        d = ds.data[:len(T)]

        # Standard
        sT, sd = standards[fields['std']]
        # Find start/end T
        start = max(sT[0], T[0]) + fields['start']
        end = min(sT[-1], T[-1]) - fields['end']
        # Cut datasets
        si = find_nearest_val(T, start, get=T.__getitem__)
        ei = find_nearest_val(T, end, get=T.__getitem__)
        logging.debug( 'Cutting', si, ei)
        T = T[si:ei]
        d = d[si:ei]
        logging.debug('T start, end', start, end)
        f = InterpolatedUnivariateSpline(sT, sd, k=2)
        s0 = f(T[0])
        s_slope = (f(T[-1]) - s0) / (T[-1] - T[0]) # Standard slope
        self.f = f
        self.s_slope = s_slope

        # Just use to get linearity residuals
        (quad, slope, const), res, rank, sing, rcond = np.polyfit(
            T, d, 2, full=True)
        self.quad = quad
        z_slope = (d[-1] - d[0]) / (T[-1] - T[0]) # Sample slope
        z_const = ds.data[0]
        res = np.sqrt(res[0] / len(T))
        # Convert from percentage to micron
        um = res * self.inidim / 100
        factor = s_slope / z_slope
        micron = u'\u03bcm'
        msg = _('Calibration factor: {} \nStandard deviation: \n    {} %\n    {} {}').format(
            factor, res, um, micron)
        self.msg = msg
        self.slope, self.const = slope, const
        self.fld, self.ds, self.T, self.d, self.sT, self.sd = fields, ds, T, d, sT, sd
        self.factor, self.res, self.um = factor, res, um
        if fields['label']:
            self.label()
        if fields['add']:
            self.add_datasets(si, d[0])
        self.apply_ops()
        self.doc.model.refresh()
        return factor, res

    def add_datasets(self, start_index, start_value):
        """Add standard and fitted datasets for further evaluations (plotting, etc)"""
        # Adding plot data
        fields = self.fld
        name = fields['std'].replace(' ', '_')
        p = fields['d'] + '/' + name
        Tds = self.doc.data[fields['T']]
        T = Tds.data
        old_unit = getattr(self.ds, 'old_unit', 'percent')
        # Fitting
#		f=np.poly1d((self.slope,0))
        f = np.poly1d((self.quad, self.slope, 0))
        df = f(T)
        df += start_value - df[start_index]
        # TODO: define new derived datasets for these
        dsf = copy(Tds)
        dsf.attr = dict({}, **Tds.attr)
        dsf.tags = set([])
        dsf.data = plugins.numpyCopyOrNone(df)
        dsf.m_var = name + '_fit'
        dsf.m_pos = 2
        dsf.m_name = dsf.m_var
        dsf.m_col = dsf.m_var
        dsf.old_unit = old_unit
        dsf.unit = 'percent'
        dsf.m_initialDimension = self.inidim
        dsf.m_label = _('Calibration Fitting')
        self.ops.append(
            document.OperationDatasetSet(p + '_fit', dsf))

        # Evaluate std fit over regular T
        d = self.f(T)
        # Translate zero so it matches the fit
        d -= d[start_index] - df[start_index]
        dsd = copy(Tds)
        dsd.attr = dict({}, **Tds.attr)
        dsd.tags = set([])
        dsd.data = plugins.numpyCopyOrNone(d)
        dsd.m_var = name
        dsd.m_pos = 1
        dsd.m_name = name
        dsd.m_col = name
        dsd.unit = 'percent'
        dsd.old_unit = old_unit
        dsd.m_initialDimension = self.inidim
        dsd.m_label = _(name)
        self.ops.append(
            document.OperationDatasetSet(p, dsd))

    def label(self):
        """Draw label"""
        cur = self.fld.get('currentwidget')
        g = self.doc.resolveFullWidgetPath(cur)
        g = utils.searchFirstOccurrence(g, ['graph', 'page'])
        if g is None or g.typename not in ['graph', 'page']:
            raise plugins.ToolsPluginException(
                'Impossible to draw the label. Select a page or a graph.')
        name = 'lbl_' + self.fld['d'].replace('summary/', '').replace('/', '_')
        if not g.getChild(name):
            self.ops.append(document.OperationWidgetAdd(g, 'label', name=name))
            self.apply_ops(self.name + ':CreateLabel')
        lbl = g.getChild(name)
        self.toset(lbl, 'label', self.msg.replace('\n', '\\\\'))


plugins.toolspluginregistry.append(CalibrationFactorPlugin)
