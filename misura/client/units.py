# -*- coding: utf-8 -*-
"""Unit conversion"""
from math import *
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

base_units = {'micron': 'length',
              'micron^3': 'volume',
              'micron^2': 'area',
              'degree': 'angle',
              'celsius': 'temperature',
              'celsius/min': 'heating rate',
              'second': 'time',
              'percent': 'part',
              'hertz': 'frequency',
              'kilobyte': 'memory',
              'poise': 'viscosity',
              'cm^2/s': 'diffusivity',
              'gram': 'weight',
              'volt': 'tension',
              'ohm': 'resistance',
              'volt/second': 'tensionRate'}

from_base = {'length': {'micron': lambda v: v,
                        'nanometer': lambda v: v * 1E3,
                        'millimeter': lambda v: v * 1E-3,
                        'centimeter': lambda v: v * 1E-4,
                        'meter': lambda v: v * 1E-6,
                        },
             # area
             'area': {'micron^2': lambda v: v, 'nanometer^2': lambda v: v * 1E6, 'millimeter^2': lambda v: v * 1E-6},
             # volume
             'volume': {'micron^3': lambda v: v, 'nanometer^3': lambda v: v * 1E9, 'millimeter^3': lambda v: v * 1E-9},
             # angle
             'angle': {'degree': lambda v: v, 'radian': lambda v: pi * v / 180.},
             # temperature
             'temperature': {'celsius': lambda v: v, 'kelvin': lambda v: v + 273.15, 'fahrenheit': lambda v: 32 + (9 * v / 5.)},
             'heating rate': {'celsius/min': lambda v: v, 'kelvin/min': lambda v: v + 273.15, 'fahrenheit/min': lambda v: 32 + (9 * v / 5.)},
             # time
             'time': {'millisecond': lambda v: v * 1000., 'second': lambda v: v, 'minute': lambda v: v / 60., 'hour': lambda v: v / 3600., 'day': lambda v: v / 86400.},
             'part': {'percent': lambda v: v, 'permille': lambda v: v * 10., 'permyriad': lambda v: v * 100.,
                      'ppm': lambda v: v * 10000., 'ppb': lambda v: v * (1.E7), 'ppt': lambda v: v * (1.E10)},
             'frequency': {'hertz': lambda v: v, 'kilohertz': lambda v: v / 1000.},
             'memory': {
    'byte': lambda v: v * 1000,
    'kilobyte': lambda v: v,
    'megabyte': lambda v: v * 1E-3,
    'gigabyte': lambda v: v * 1E-6,
},
    'viscosity': {'poise': lambda v: v * 10,
                  'pascal/s': lambda v: v,
                  },
    'diffusivity': {'cm^2/s': lambda v: v,
                    'm^2/s': lambda v: v * 1E-4,
                    'mm^2/s': lambda v: v * 1E2,
                    },
    'weight': {'gram': lambda v: v,
               'kilogram': lambda v: v * 1E-3,
               'milligram': lambda v: v * 1E3
               },
    'tension': {'volt': lambda v: v,
                'millivolt': lambda v: v * 1E3
                },
    'resistance': {'ohm': lambda v: v,
                   'milliohm': lambda v: v * 1E3,
                   'megaohm': lambda v: v * 1E-6,
                   },
    'tensionRate': {'volt/second': lambda v: v},
}

derivatives = {'length': {'micron': 1,
                          'nanometer': 1E3,
                          'millimeter': 1E-3,
                          'centimeter': 1E-4,
                          'meter': 1E-6},
               'area': {'micron^2': lambda v: v, 'nanometer^2': lambda v: v * 1E6, 'millimeter^2': lambda v: v * 1E-6},
               'volume': {'micron^3': lambda v: v, 'nanometer^3': lambda v: v * 1E9, 'millimeter^3': lambda v: v * 1E-9},
               'angle': {'degree': 1, 'radian': pi / 180.},  # angle
               'temperature': {'celsius': 1, 'kelvin': 1, 'fahrenheit': 9 / 5.},
               'heating rate': {'celsius/min': 1, 'kelvin/min': 1, 'fahrenheit/min': 9 / 5.},
               'time': {'millisecond': 1000., 'second': 1., 'minute': 1 / 60., 'hour': 1 / 3600., 'day': 1 / 86400.},
               'part': {'percent': 1, 'permille': 10., 'permyriad': 100.,  # parts
                        'ppm': 10000., 'ppb': 1.E7, 'ppt': 1.E10},
               'frequency': {'hertz': 1, 'kilohertz': 1 / 1000.},  # freq
               'memory': {
    'byte': 1000,
    'kilobyte': 1,
    'megabyte': 1E-3,
    'gigabyte': 1E-6,
},
    'viscosity': {
    'poise': 10,
    'pascal/s': 1,
},
    'diffusivity': {'cm^2/s': 1,
                    'm^2/s': 1E-4,
                    'mm^2/s': 1E2,
                    },
    'weight': {'gram': 1,
               'kilogram': 1E-3,
               'milligram': 1E3
               },
    'tension': {'volt': 1,
                'millivolt': 1E3
                },
    'resistance': {'ohm': 1,
                   'milliohm': 1E3,
                   'megaohm': 1E-6,
                   },
    'tensionRate': {'volt/second': 1},
}

to_base = {'length': {'micron': lambda v: v,
                      "nanometer": lambda v: v * 1E-3,
                      'millimeter': lambda v: v * 1E3,
                      'centimeter': lambda v: v * 1E4,
                      'meter': lambda v: v * 1E6,
                      },
           # area
           'area': {'micron^2': lambda v: v, 'nanometer^2': lambda v: v * 1E-6, 'millimeter^2': lambda v: v * 1E6},
           # volume
           'volume': {'micron^3': lambda v: v, 'nanometer^3': lambda v: v * 1E-9, 'millimeter^3': lambda v: v * 1E9},
           # angle
           'angle': {'degree': lambda v: v, 'radian': lambda v: v * 180. / pi},
           # temperature
           'temperature': {'celsius': lambda v: v, 'kelvin': lambda v: v - 273.15, 'fahrenheit': lambda v: 5 * (v - 32) / 9},
           'heating rate': {'celsius/min': lambda v: v, 'kelvin/min': lambda v: v - 273.15, 'fahrenheit/min': lambda v: 5 * (v - 32) / 9},
           # time
           'time': {'millisecond': lambda v: v / 1000., 'second': lambda v: v, 'minute': lambda v: v * 60., 'hour': lambda v: v * 3600., 'day': lambda v: v * 86400.},
           'part': {'percent': lambda v: v, 'permille': lambda v: v / 10., 'permyriad': lambda v: v / 100.,  # parts
                    'ppm': lambda v: v / 10000., 'ppb': lambda v: 1. * v / (10 ** 7), 'ppt': lambda v: 1. * v / 10 ** 10},  # freq
           'frequency': {'hertz': lambda v: v, 'kilohertz': lambda v: v * 1000.},
           'memory': {
    'byte': lambda v: v * 1E-3,
    'kilobyte': lambda v: v,
    'megabyte': lambda v: v * 1E3,
    'gigabyte': lambda v: v * 1E6,
},
    'viscosity': {
    'poise': lambda v: v * 0.1,
    'pascal/s': lambda v: v,
},
    'diffusivity': {'cm^2/s': lambda v: v,
                    'm^2/s': lambda v: v * 1E4,
                    'mm^2/s': lambda v: v * 1E-2,
                    },
    'weight': {'gram': lambda v: v,
               'kilogram': lambda v: v * 1E3,
               'milligram': lambda v: v * 1E-3},
    'tension': {'volt': lambda v: v,
                'millivolt': lambda v: v * 1E-3,
                },
    'resistance': {'ohm': lambda v: v,
                   'milliohm': lambda v: v * 1E-3,
                   'megaohm': lambda v: v * 1E6,
                   },
    'tensionRate': {'volt/second': lambda v: v},
}

# Latex symbols for Veusz
symbols = {'micron': '{\mu}m', 	'nanometer': 'nm', 	'millimeter': 'mm',
           'centimeter': 'cm', 'meter': 'm',
           'micron^3': '{{\mu}m^3}', 'micron^2': '{{\mu}m^2}',
           'nanometer^3': '{nm^3}', 'nanometer^2': '{nm^2}',
           'millimeter^3': '{mm^3}', 'millimeter^2': '{mm^2}',
           'degree': '{\deg}', 	'radian': 'rad',
           'celsius': '{\deg}C', 'kelvin': '{\deg}K', 	'fahrenheit': '{\deg}F',
           'celsius/min': '{\deg}C/min', 'kelvin': '{\deg}K/min',     'fahrenheit': '{\deg}F/min',
           'second': 's', 'minute': 'min', 'hour': 'hr', 'day': 'd', 'millisecond': 'ms',
           'percent': '%', 'permille': '{\\textperthousand}',
           'hertz': 'Hz', 'kilohertz': 'kHz',
           'byte': 'B',
           'kilobyte': 'KB',
           'megabyte': 'MB',
           'gigabyte': 'GB',
           'poise': 'P',
           'pascal/s': 'Pa/s',
           'cm^2/s': u'{cm^2}{s^-1}',
           'm^2/s': u'{m^2}{s^-1}',
           'mm^2/s': u'{mm^2}{s^-1}',
           'gram': 'g',
           'milligram': 'mg',
           'kilogram': 'kg',
           'volt': 'V',
           'millivolt': 'mV',
           'ohm': '\Omega', 'milliohm': 'm\Omega', 'megaohm': 'M\Omega',
           'volt/second': 'V/s',
           }

# HTML symbols for Qt
hsymbols = symbols.copy()
hsymbols.update({'micron': u'\u03bcm', 'micron^2': u'\u03bcm²', 'micron^3': u'\u03bcm³',
                 'nanometer^2': u'nm²', 'nanometer^3': u'nm³',
                 'millimeter^2': u'mm²', 'millimeter^3': u'mm³',
                 'degree': u'°',
                 'celsius': u'°C', 'kelvin': u'°K', 'fahrenheit': u'°F',
                 'celsius/min': u'°C/min', 'kelvin/min': u'°K/min', 'fahrenheit/min': u'°F/min',
                 'permille': u'\u2030',
                 'pixel': 'px',
                 'cm^2/s': u'cm²s⁻¹',
                 'm^2/s': u'm²s⁻¹',
                 'mm^2/s': u'mm²s⁻¹',
                 'ohm': u'\u03A9', 'milliohm': u'm\u03A9', 'megaohm': u'M\u03A9',
                 })


# Create a dictionary unit:dimension
known_units = {}
for d, u in from_base.iteritems():
    for v in u.iterkeys():
        known_units[v] = d

# TODO: resolve composed units; eg: A/B, A*B/C, etc

# TODO: translate into settings. Function to change all loaded options?
user_defaults = {'length': 'micron',
                 'area': 'micron^2',
                 'volume': 'micron^3',
                 'angle': 'degree',
                 'temperature': 'celsius',
                 'time': 'second',
                 'part': 'percent',
                 'viscosity': 'posie',
                 'diffusivity': 'cm^2/s',
                 'weight': 'gram',
                 'tension': 'volt',
                 'resistance': 'ohm',
                 'tensionRate': 'volt/second',
                 }


def get_unit_info(unit, units):
    logging.debug('%s %s', 'get_unit_info', unit)
    p = unit.split('^')
    u = p[0]
    if len(p) == 2:
        p = int(p[1].split('/')[0])
    else:
        p = 1
# 	print units
    for key, group in units.iteritems():
        # Get unit conversion function
        if not group.has_key(unit):
            continue
        return key, group[unit], p
    return None, None, p


class Converter(object):
    from_server = lambda val: val
    '''Convert `val` from server-side unit into client-side unit'''
    to_client = from_server
    '''Alias'''
    from_client = lambda val: val
    '''Convert `val` from client-side unit into server-side unit'''
    to_server = from_client
    '''Alias'''
    d = 1
    """Derivative factor for the conversion server->client"""
    unit = None

    @classmethod
    def convert_func(cls, from_unit, to_unit):
        """Returns the conversion function from `from_unit` to `to_unit`"""
        if from_unit in ('None', None):
            return lambda val: val
        if from_unit == to_unit:
            return lambda val: val
        if to_unit == None:
            dom = known_units[from_unit]
            to_unit = user_defaults[dom]
        c = cls(from_unit, to_unit)
        return c.from_server

    @classmethod
    def convert(cls, from_unit, to_unit, val):
        """Direct conversion of `val` from `from_unit` to `to_unit`"""
        func = cls.convert_func(from_unit, to_unit)
        return func(val)

    def __init__(self, unit, csunit):
        if not unit:
            unit = ''
        x = unit.count('*')
        d = unit.count('/')
        p = unit.count('^')
        if x + d + p == 0:
            if not known_units.has_key(unit):
                unit = 'None'
            self.unit = unit
        # ...
        self.csunit = csunit

        if self.csunit == self.unit or 'None' in [self.unit, self.csunit]:
            # No conversion needed or possible
            self.from_server = lambda val: val
            self.from_client = lambda val: val
        else:
            group = known_units[csunit]
            print 'group,unit', group, unit, csunit
            cfb = from_base[group][csunit]  # client-to-base
            ctb = to_base[group][self.csunit]  # client-to-base
            # How to manage different groups?
            # cud = derivatives[group][csunit]
            # sud = derivatives[group][unit]

            if base_units.has_key(unit):
                # If the server unit is a base unit, return the direct conversion
                # to client-side unit
                self.from_server = cfb
                # Conversion derivative server->client
                # self.d = cud
                # return the direct conversion from client-side unit
                self.from_client = ctb
                # Conversion derivative client->server
            else:
                # Otherwise, convert the value to its base unit,
                # then convert this new value to client-side unit
                stb = to_base[group][unit]  # server-to-base
                self.from_server = lambda val: cfb(stb(val))
                # Conversion derivative client->server
                # self.d = sud
                # convert the value from client-side unit to its base unit,
                # then convert this new value to the actual server-side unit
                sfb = from_base[group][unit]
                self.from_client = lambda val: sfb(ctb(val))


import veusz.plugins as plugins
from copy import copy
import numpy as np


def get_from_unit(ds, to_unit):
    """Get starting conversion unit for dataset `ds0` to convert it to `to_unit`"""
#     ds = getattr(ds0, 'pluginds', ds0)
    from_unit = getattr(ds, 'unit', False)
    if not from_unit or to_unit in ['None', '', None, False]:
        raise plugins.DatasetPluginException(
            'Selected dataset does not have a measurement unit.')
    # Implicit To-From percentile conversion
    from_group = known_units[from_unit]
    to_group = known_units[to_unit]
    if from_group != to_group:
        if 'part' not in (from_group, to_group):
            raise plugins.DatasetPluginException(
                'Incompatible conversion: from {} to {}'.format(from_unit, to_unit))
        if to_group == 'part':
            from_unit = 'percent'
        elif from_group == 'part':
            # Guess default unit for destination dimension
            from_unit = getattr(ds, 'old_unit', user_defaults[to_group])

    return from_unit, to_unit, from_group, to_group


def convert_func(ds, to_unit):
    """Returns conversion function which can be applied over an array or value
    to convert `ds0` to `to_unit`"""
#     ds = getattr(ds0, 'pluginds', ds0)
    from_unit, to_unit, from_group, to_group = get_from_unit(ds, to_unit)
    func = Converter.convert_func(from_unit, to_unit)
    ret = func
    # If groups differ, concatenate a percentile conversion to func
    if from_group != to_group:
        action = percentile_action(ds, 'Invert')
        pfunc = percentile_func(ds, action)
        ret = lambda out: func(pfunc(out))
    return ret


def convert(ds, to_unit):
    """Convert dataset `ds` to `to_unit`.
    Returns a new dataset."""
    # In case ds derived from a plugin, return the original plugin dataset
#     ds = getattr(ds0, 'pluginds', ds0)
    from_unit, to_unit, from_group, to_group = get_from_unit(ds, to_unit)
    func = convert_func(ds, to_unit)

    ds1 = copy(ds)
    out = func(np.array(ds1.data))
    ds1.data = plugins.numpyCopyOrNone(out)
    ds1.unit = to_unit
    ds1.m_percent = to_group == 'part'

    ini = getattr(ds, 'm_initialDimension', 0)
    old_unit = getattr(ds, 'old_unit', from_unit)
    old_group = known_units.get(old_unit, None)
    if ini and (old_group == to_group == from_group) and 'part' != to_group:
        ini1 = func(ini)
        ds.m_initialDimension = ini1
        ds1.m_initialDimension = ini1
        logging.debug('%s %s %s', 'converting m_initialDimension', ini, ini1)
    return ds1


def percentile_action(ds, action='Invert'):
    """Autodetect percentile conversion action to be performed"""
    cur = getattr(ds, 'm_percent', False)
    # invert action
    if action == 'Invert':
        if cur:
            action = 'To Absolute'
        else:
            action = 'To Percent'
    logging.debug('percentile_action %s', action)
    return action


def percentile_func(ds, action='To Absolute', auto=True):
    """Returns the function used to convert dataset `ds` to percent or back to absolute"""
    ini = getattr(ds, 'm_initialDimension', False)
    # Auto initial dimension
    if not ini:
        if not auto or action != 'To Percent':
            raise plugins.DatasetPluginException('Selected dataset does not have an initial dimension set. \
        Please first run "Initial dimension..." tool. {}{}{}'.format(action, ds.m_col, ds.m_initialDimension))
        ds.m_initialDimension = np.array(ds.data[:5]).mean()

    if action == 'To Absolute':
        u = getattr(ds, 'unit', 'percent')
        # If current dataset unit is not percent, convert to
        convert_func = Converter.convert_func(u, 'percent')
        func = lambda out: convert_func(out * ds.m_initialDimension / 100.)
    elif action == 'To Percent':
        func = lambda out: 100. * out / ds.m_initialDimension
    return func


def percentile_conversion(ds, action='Invert', auto=True):
    ds = copy(ds)
    action = percentile_action(ds, action)
    func = percentile_func(ds, action, auto)
    out = func(np.array(ds.data))

    # Evaluate if the conversion is needed
    # based on the current status and the action requested by the user
    if action == 'To Absolute':
        ds.m_percent = False
        u = getattr(ds, 'unit', 'percent')
        ds.unit = getattr(ds, 'old_unit', False)
        ds.old_unit = u
    elif action == 'To Percent':
        ds.m_percent = True
        ds.old_unit = getattr(ds, 'unit', False)
        ds.unit = 'percent'
    ds.data = plugins.numpyCopyOrNone(out)
    return ds
