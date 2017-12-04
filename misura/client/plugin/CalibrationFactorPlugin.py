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
standards = {}

    # https://www-s.nist.gov/srmors/view_cert.cfm?srm=738
standards['NIST-SRM738'] = np.array([
            (20, 0),
            (27, 69),
            (67, 466),
            (107, 872),
            (147, 1288),
            (187, 1714),
            (227, 2149),
            (267, 2593),
            (307, 3048),
            (347, 3511),
            (387, 3984),
            (427, 4467),
            (467, 4959),
            (507, 5461)
            ], dtype=np.float32) 
standards['NIST-SRM738'][:,1]*=10**-4

# http://www.ceramics.nist.gov/srd/summary/scdaos.htm
standards['Al2O3'] = np.array([	
    (0,	0),
    (20, 92),
    (500, 3550),
    (1000,8100),
    (1200,9960),
    (1400,11900),
     (1500,12900)], dtype=np.float32)

standards['Al2O3'][:,1]*=10**-4


# http://www.ceramics.nist.gov/srd/scd/Z00665.htm
standards['Al2O3-Dil'] = np.array([
    (0,   0),
    (27,  150.93),
    (77,  442.74),
    (127, 767.08),
    (177, 1116.87),
    (227, 1484.58),
    (277, 1869.75),
    (327, 2266.11),
    (377, 2672.93),
    (427, 3087.21),
    (477, 3510.72),
    (527, 3941.96),
    (627, 4809.09),
    (727, 5699.68),
    (827, 6591.19),
    (927, 7490.16),
    (1027, 8390.59),
    (1127, 9297.75),
    (1227, 10208.64),
    (1327, 11120.26),
    (1427, 12043.88),
    (1527, 12964.23),
    (1627, 13878.31),
    (1727, 14800.39)], dtype=np.float32)
standards['Al2O3-Dil'][:,1]*=10**-4



# http://www.ceramics.nist.gov/srd/scd/Z00662.htm
standards['Al2O3-N-Diffraction'] = np.array([
    (20,    0),
    (100,   756.6),
    (200,   1540.8),
    (300,   2343.6),
    (400,   3165.6),
    (500,   4012),
    (600,   4806),
    (700,   5732.3),
    (800,   6624.8),
    (900,   7535.7),
    (1000,  8468),
    (1100,  9408.3),
    (1200,  10368),
    (1300,  11349),
    (1400,  12335.4),
    (1500,  13360.5),
    (1600,  14387.2),
    (1700,  15436),
    (1800,  16507.8),
    (1900,  17584.5 ),
    (2000,  18696 ),
    (2050,  19247.45)], dtype=np.float32)

standards['Al2O3-N-Diffraction'][:,1]*=10**-4


# Calibration certificate RU 01 N.2416-681-04028
# Kelvin
standards['Sapphire'] =  np.array([
    (90,  -624.2),
    (110,  -609.5),
    (130,  -583.2),
    (150,  -545.8),
    (170,  -497.6),
    (190,  -439.3),
    (210,  -371.5),
    (230,  -294.7),
    (250,  -209.4),
    (270,  -116.2),
    (340,  264.2),
    (390,  577.6),
    (440,  916.7),
    (490,  1275.8),
    (540,  1651.4),
    (590,  2048.8),
    (640,  2441.5),
    (690,  2850.4),
    (740,  3266.1),
    (790,  3688.1),
    (840,  4116.1),
    (890,  4550.4),
    (940,  4990.8),
    (990,  5437.3),
    (1040,  5890.2),
    (1090,  6349.2),
    (1140,  6814.4),
    (1190,  7285.7),
    (1240,  7763.2),
    (1290,  8247),
    (1340,  8736.9),
    (1390,  9232.9),
    (1440,  9735.2),
    (1490,  10244.9),
    (1540,  10759.2),
    (1590,  11280.1),
    (1640,  11807.1),
    (1690,  12340.3),
    (1740,  12879.7),
    (1790,  13425.1),
    (1900,  14575.5),
    (2000,  15704.4)], dtype=np.float32)
# Convert to celsius
standards['Sapphire'][:,0] -= 273.15
standards['Sapphire'][:,1] *= 10**-4

    # DE Data table
standards['Platinum'] = np.array([
    (20, 0),
    (500, 4642  ),
    (1000,10104),
    (1200,  12549 ),
    (1400,  15169),
    (1500, 16563)], dtype=np.float32)
standards['Platinum'][:,1]*=10**-4
 
 



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
        self.T = T
        # Cut away any cooling
        while max(T) != T[-1]:
            i = np.where(T == max(T))[0]
            T = T[:i]
        d = ds.data[:len(T)]

        # Standard
        S = standards[fields['std']]
        sT = S[:,0]
        sd = S[:,1]
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

        # Standard slope
        f = InterpolatedUnivariateSpline(sT, sd, k=2)
        s0 = f(T[0])
        s_slope = (f(T[-1]) - s0) / (T[-1] - T[0]) 
        self.f = f
        self.s_slope = s_slope

        # Just use to get linearity residuals
        self.fitting = np.polyfit(T, d, 2, full=True)
        (quad, slope, const), res, rank, sing, rcond = self.fitting
        
        self.quad = quad
        self.slope, self.const = slope, const
        
        #self.std_fitting = np.polyfit(d-d[0], d-d[0]-f(T)+f(T[0]), 2, full=True)
        #self.std_quad, self.std_slope, self.std_const = self.std_fitting[0]
        
        z_slope = (d[-1] - d[0]) / (T[-1] - T[0]) # Sample slope
        z_const = ds.data[0]
        res = np.sqrt(res[0] / len(T))
        # Convert from percentage to micron
        um = res * self.inidim / 100
        factor = s_slope / z_slope
        
        
        micron = u'\u03bcm'
        msg = _('Calibration factor: {} \nStandard deviation: \n    {} %\n    {} {}').format(
            factor, res, um, micron)
        #msg += _('\nLinear: {} \nSquared: {}'.format(self.std_slope/self.slope,
        #                                            self.std_quad/self.quad))
        
        self.msg = msg
        logging.debug(msg)
        
        self.fld, self.ds, self.d, self.sT, self.sd = fields, ds, d, sT, sd
        self.factor, self.res, self.um = factor, res, um
        if fields['label']:
            self.label()
        if fields['add']:
            self.add_datasets(si, ei, d[0])
        self.apply_ops()
        self.doc.model.refresh()
        return factor, res

    def add_datasets(self, start_index, end_index, start_value):
        """Add standard and fitted datasets for further evaluations (plotting, etc)"""
        #TODO: convert these into derived datasets
        # Adding plot data
        fields = self.fld
        name = fields['std'].replace(' ', '_')
        p = fields['d'] + '/' + name
        Tds = self.doc.data[fields['T']]
        old_unit = getattr(self.ds, 'old_unit', 'percent')
        # Fitting
#		f=np.poly1d((self.slope,0))
        f = np.poly1d((self.quad, self.slope, 0))
        df = f(self.T)
        df += start_value - df[start_index]
        df[:start_index] = None
        df[end_index:] = None
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
        d = self.f(self.T)
        # Translate zero so it matches the fit
        d -= d[start_index] - df[start_index]
        d[:start_index] = None
        d[end_index:] = None
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
