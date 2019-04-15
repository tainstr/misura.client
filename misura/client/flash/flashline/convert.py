#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
"""Converts from FlashLine to Misura 4 data formats"""
import os
from datetime import datetime
from time import mktime, sleep
from time import localtime, strftime
import collections
from copy import deepcopy
import multiprocessing
from traceback import format_exc

import numpy as np
from scipy.interpolate import interp1d

from misura.canon import option, indexer, reference
from misura.canon.option import ao
from misura.canon.logger import get_module_logging
from misura.client.flash.reference_files import calc_reference_data
from misura.client.flash.flashline.debug_table import fake_debug_table
from __builtin__ import True
mlogging = get_module_logging(__name__)
from misura.canon.plugin import dataimport
from misura.client.flash.reference_files import list_reference_files


from . import dataparser
from .dataparser import get_data
from . import debug_table as d_t
from . import diagnostic
from .log_files import parse_all_logs



logging = dataimport.SelectLogging()

# TODO: define a "laser" device, an mcc device, etc
result_handles = [('halftime', 'HalfTime', 0),
                  ('clarkTaylor', 'Clark&Taylor', 0),
                  ('degiovanni', 'Degiovanni', 0),
                  ('parker', 'Parker', 0),
                  ('koski', 'Koski', 3),
                  ('heckman', 'Heckman', 3),
                  ('cowan5', 'Cowan(5)', 3),
                  ('cowan10', 'Cowan(10)', 3),
                  ('clarkTaylor1', 'Clark&Taylor(1)', 3),
                  ('clarkTaylor2', 'Clark&Taylor(2)', 3),
                  ('clarkTaylor3', 'Clark&Taylor(3)', 3),
                  ]

extra_handles = [('density', 'Density', 0),
                 ('expansion', 'Expansion', 0),
                 ('specificHeatRef', 'Specific Heat Reference', 0),
                 ('thickness', 'Thickness', 0),
                 ]


def add_results_options(out, confdb, **kwargs):
    """Add results to `out`"""
    if not kwargs.has_key('attr'):
        kwargs['attr'] = []
    with_errors = kwargs.pop('with_errors', False)
    kwargs['attr'].append('ReadOnly')
    kwargs['attr'].append('Result')
    kwargs['attr'] = list(set(kwargs['attr']))
    kwargs['precision'] = 5
    # Fake fullpath
    fp = '/flash/sampleX/'
    for handle, title, auth in result_handles:
        kwargs['readLevel'] = auth
        if handle == 'halftime':
            kwargs['unit'] = 'second'
        else:
            kwargs['unit'] = 'cm^2/second'
        if with_errors and handle != 'reference':
            kwargs['error'] = handle + 'Error'
            
        a = kwargs['attr']
        if handle == 'reference':
            a.append('Hidden')
        elif 'Hidden' in a:
            a.remove('Hidden')
        if confdb.rule_opt_hide(fp+handle):
            if 'ClientHide' not in a:
                a.append('ClientHide')
        elif 'ClientHide' in kwargs['attr']:
            a.remove('ClientHide')
        kwargs['attr'] = a
        ao(out, handle, 'Float',
           name=title, **deepcopy(kwargs))

    if with_errors:
        kwargs.pop('error')
        kwargs.pop('aggregate')
        add_error_options(out, **deepcopy(kwargs))


def add_error_options(out, **kwargs):
    kwargs['attr'].append('Event')
    for handle, title, auth in result_handles:
        kwargs['readLevel'] = auth
        if handle == 'halftime':
            kwargs['unit'] = 'second'
        else:
            kwargs['unit'] = 'cm^2/second'
        if handle == 'reference':
            kwargs['attr'].append('Hidden')
        elif 'Hidden' in kwargs['attr']:
            kwargs['attr'].remove('Hidden')
        ao(out, handle + 'Error', 'Float',
           name=title + ' Error',
           parent=handle,
           **deepcopy(kwargs))


diffusivity_table = [[('Time', 'Float'),
                      ('Temp.', 'Float'),
                      ('Value', 'Float'),
                      ]]

mean_diffusivity_table = [[('Time', 'Float'),
                           ('Temp.', 'Float'),
                           ('Value', 'Float'),
                           ('Error', 'Float'),
                           ]]


def ref_name(h0):
    """Calculate corresponding reference name for result `h0`"""
    return h0 + 'Ref'


# Aggregation string generators
rh = [ref_name(r[0]) for r in result_handles[:-1] + [('jg2d_diffusivity', ''), ('inpl_diffusivity', ''),
                                                     ('ml2_diffusivity2', ''), ('ml3_diffusivity3', '')]]

rhn = ', ' + (', '.join(rh))


def f_aggreg(name):
    r = 'table(time, temperature, {0}'.format(name)
    if name != 'reference':
        r += ', {}Ref, reference'.format(name)
    return r + ')'


def f_aggreg_err(name):
    r = 'table(time, temperature, {0}, {0}Error, setpoint'.format(name)
    if name != 'reference':
        r += ', {}Ref, reference'.format(name)
    return r + ')'


def f_aggreg_multi(*names, **k):
    """Used for segments"""
    tmp = ('{}, ' * len(names)).format(*names)[:-2]
    return 'table({})'.format(tmp)


def f_aggreg_err_multi(*names, **k):
    """Used for samples"""
    sub = ''
    for name in names:
        sub += '{0}, {0}Error, '.format(name)
    return 'table_flat(setpoint, {})'.format(sub[:-2])


def add_results_tables(out, confdb, **kwargs):
    if not kwargs.has_key('attr'):
        kwargs['attr'] = []
    kwargs['attr'].append('ReadOnly')
    kwargs['attr'].append('Result')
    kwargs['attr'] = list(set(kwargs['attr']))
    kwargs['precision'] = [0, 1, 4]
    kwargs['visible'] = [0, 1, 1]
    kwargs['unit'] = ['second', 'celsius', 'cm^2/second']
    f = f_aggreg
    tab = diffusivity_table
    with_errors = kwargs.pop('with_errors', False)
    if with_errors:
        f = f_aggreg_err
        kwargs['unit'].append('cm^2/second')
        tab = mean_diffusivity_table
        kwargs['precision'].append(4)
        kwargs['visible'].append(1)

        kwerr = deepcopy(kwargs)
        kwerr['attr'].append('Hidden')
        kwerr['unit'] = 'cm^2/second'
        kwerr['precision'] = 4
        kwerr['attr'].append('Event')
    
    # Fake fullpath
    fp = '/flash/sampleX/'
    for handle, title, auth in result_handles:
        kwargs['readLevel'] = auth
        if handle == 'halftime':
            kwargs['unit'][2] = 'second'
            if with_errors:
                kwargs['unit'][3] = 'second'
                kwerr['unit'] = 'second'
        else:
            kwargs['unit'][2] = 'cm^2/second'
            if with_errors:
                kwargs['unit'][3] = 'cm^2/second'
                kwerr['unit'] = 'cm^2/second'
        if with_errors:
            kwargs['error'] = handle + 'sError'
        if handle == 'reference':
            kwargs['attr'].append('Hidden')
        elif 'Hidden' in kwargs['attr']:
            kwargs['attr'].remove('Hidden')
        if confdb.rule_opt_hide(fp+handle):
            if 'ClientHide' not in kwargs['attr']:
                kwargs['attr'].append('ClientHide')
        elif 'ClientHide' in kwargs['attr']:
            kwargs['attr'].remove('ClientHide')
        ao(out, handle + 's', 'Table',
           tab[:],
           name=title,
           aggregate=f(handle),
           **deepcopy(kwargs))
        if with_errors:
            ao(out, handle + 'sError', 'Float',
               0.0,
               name=title + ' Error',
               **deepcopy(kwerr))


def add_summary_table(out, **kwargs):
    """Create a summary table comprising all result handles"""
    if not kwargs.has_key('attr'):
        kwargs['attr'] = []
    kwargs['attr'].append('ReadOnly')
    kwargs['attr'].append('Result')
    kwargs['attr'] = list(set(kwargs['attr']))
    with_errors = kwargs.pop('with_errors', False)
    # Add cross tables
    tab = [[('Temp.', 'Float')]]
    visible = [1]
    precision = [0]
    unit = ['celsius']
    handles = []
    for handle, name, level in result_handles:
        if handle == 'reference':
            continue
        handles.append(handle)
        tab[0].append((name, 'Float'))
        u = 'second' if handle == 'halftime' else 'cm^2/second'
        unit.append(u)
        precision.append(4)
        # View only most important
        visible.append(level < 3)
        # Add error column
        if with_errors:
            tab[0].append((name + ' Error', 'Float'))
            unit.append(u)
            precision.append(4)
            # Hide errors
            visible.append(0)

    if with_errors:
        # Samples
        kwargs['aggregate'] = f_aggreg_err_multi(*handles)
    else:
        # Segments
        handles.insert(0,'temperature')
        kwargs['aggregate'] = f_aggreg_multi(*handles)

    kwargs['precision'] = precision
    kwargs['visible'] = []  # visible
    kwargs['unit'] = unit
    
    ao(out, 'summary', 'Table',
       tab,
       rotate=True,
       name='Summary',
       **kwargs)
    return out


def add_merge_tables(instrobj, **kwargs):
    """Create a merged table from all sample tables"""
    if not kwargs.has_key('attr'):
        kwargs['attr'] = []
    kwargs['attr'].append('ReadOnly')
    kwargs['attr'].append('Result')
    kwargs['attr'] = list(set(kwargs['attr']))
    # Add cross tables
    tab = [[('Temp.', 'Float')]]
    visible = [1]
    precision = [0]
    unit = ['celsius']
    # Set the index of the key column
    for smp in instrobj.samples:
        for handle, name, level in result_handles:
            if handle == 'reference':
                continue
            name = smp['name'] + '\n' + name
            tab[0].append((name, 'Float'))
            u = 'second' if handle == 'halftime' else 'cm^2/second'
            unit.append(u)
            precision.append(4)
            # View only most important
            visible.append(level < 3)
            # Add error column
            tab[0].append((name + ' Error', 'Float'))
            unit.append(u)
            precision.append(4)
            # Hide errors
            visible.append(0)

    kwargs['aggregate'] = 'merge_tables(summary)'
    kwargs['precision'] = precision
    kwargs['visible'] = []  # visible
    kwargs['unit'] = unit
    instrobj.add_option('summary', 'Table',
                        tab,
                        name='Summary',
                        rotate=True,
                        **kwargs)
    return instrobj




def smp_tree(confdb):
    """Create sample data structure"""
    out = dataimport.smp_dict()
    out['comment']['parent'] = 'name'
    out['name']['name'] = 'Sample title'
    out['mro']['current'] = ['SampleFlash']+out['mro']['current']
    out.pop('initialDimension')
    ao(out, 'position', 'Integer', name='Position')
    ao(out, 'thickness', 'Float', 1., name='Thickness',
       precision=4, unit='centimeter')
    ao(out, 'diameter', 'Float', 1., name='Diameter',
       precision=4, unit='centimeter')
    ao(out, 'weight', 'Float', 1., name='Weight', precision=4, unit='gram')
    ao(out, 'testType', 'Chooser', 1, name='Test type',
       values=[1, 2, 3, 10, 11],
       options=['Normal', 'Specific Heat', 'No laser fire', 'Tune', 'In Plane'], writeLevel=3)
    ao(out, 'expansionType', 'Chooser', 0, name='Expansion type',
       values=[0, 1, 2, 3], writeLevel=3,
       options=['None', 'Linear', 'None', 'Equation type'])
    ao(out, 'fileID', 'String', name='Sample ID', readLevel=3)
    ao(out, 'diffusivityFile', 'Chooser', 'None', name='Diffusivity Reference', writeLevel=2,
       options=list_reference_files(3), callback_set='update_reference_diffusivity', callback_get='list_reference_diffusivity')
    ao(out, 'specificHeatFile', 'Chooser', 'None', name='Specific Heat Reference', writeLevel=3,
       options=list_reference_files(1))
    ao(out, 'densityFile', 'Chooser', 'None', name='Density Reference', writeLevel=3,
       options=list_reference_files(2))
    ao(out, 'expansionFile', 'Chooser', 'None', name='Expansion Reference', writeLevel=3,
       options=list_reference_files(4))
    ao(out, 'laserGeometry', 'Chooser', name='System geometry', current='__autoguess__', readLevel=2, 
       callback_get='list_laser_geometries', callback_set='set_laser_geometry')
    ao(out, 'capsuleFileName', 'String', name='Capsule file path', readLevel=3, parent='laserGeometry')
    ao(out, 'irradiatedInner', 'Float', name='Inner irradiated diameter', parent='laserGeometry', precision=4)
    ao(out, 'irradiatedOuter', 'Float', name='Outer irradiated diameter', parent='laserGeometry', precision=4)
    ao(out, 'viewedOuter', 'Float', name='Outer viewed diameter', parent='laserGeometry', precision=4)
    ao(out, 'viewedInner', 'Float', name='Inner viewed diameter', parent='laserGeometry', precision=4)
    # Diffusivity tables, by temperature
    add_summary_table(out, with_errors=True)
    add_results_tables(out, confdb, with_errors=True)

    return collections.OrderedDict({'self': out})


def equi_dict(confdb):
    """Create equilibrium/segment data structure"""
    out = dataimport.base_dict()
    out['comment']['parent'] = 'name'
    out['name']['current'] = 'Equilibrium at '
    out['mro']['current'] = ['FlashSegment']+out['mro']['current']
    kw = {'attr':['ReadOnly']}
    ao(out, 'setpoint', 'Float', name='Setpoint', unit='celsius', precision=1, **kw)
    ao(out, 'temperature', 'Float', name='Temperature',precision=1,
       unit='celsius', aggregate='mean()')
    ao(out, 'time', 'Float', name='Shooting start time',
       unit='second', aggregate='mean()', attr=['Hidden'], readLevel=3)
    ao(out, 'stable', 'Boolean',aggregate='mean()',
       name='Stable Temperature', parent='temperature')
    ao(out, 'segment', 'Integer', name='Segment No.', readLevel=3, **kw)
    ao(out, 'shots', 'Integer', name='Shots', readLevel=3, **kw)
    # Mean diffusivity and diffusivity dataset options
    add_results_options(out, confdb,
                        attr=['Event', 'History', 'Result'],
                        aggregate='mean()', with_errors=True)
    # Diffusivity tables, by shot
    add_summary_table(out, with_errors=False)
    add_results_tables(out, confdb, with_errors=False)
    return out

def shot_dict(confdb):
    """Create shot data structure"""
    out = dataimport.base_dict()
    out['comment']['parent'] = 'name'
    out['name']['current'] = 'Shot '
    out['mro']['current'] = ['FlashShot']+out['mro']['current']
    kw = {'attr':['ReadOnly', 'Config']}
    ao(out, 'setpoint', 'Float', name='Setpoint', unit='celsius',precision=1, **kw)
    ao(out, 'temperature', 'Float', name='Temperature', unit='celsius',precision=1, **kw)
    ao(out, 'stable', 'Boolean',
       name='Stable Temperature', parent='temperature', **kw)
    ao(out, 'laserSetpoint', 'Float', name='Laser setpoint', precision=1, **kw)
    ao(out, 'laserPower', 'Float', name='Laser power', precision=1, parent='laserSetpoint', **kw)
    ao(out, 'raw', 'Float', name='Raw signal',
       unit='volt', attr=['History', 'Event', 'Runtime', 'Hidden'])
    ao(out, 'laser', 'Float',  name='Laser signal',
       unit='volt', attr=['History', 'Event', 'Runtime', 'Hidden'])
    ao(out, 'laserFit', 'Float',  name='Laser fitting',
       unit='volt', attr=['History', 'Event', 'Runtime', 'Hidden'])
    ao(out, 'time', 'Float', name='Start time of the shot', attr=['Hidden'],
       unit='second', readLevel=3)
    ao(out, 'duration', 'Float', name='Shot duration',
       unit='second', readLevel=3, **kw)
    ao(out, 'frequency', 'Float', name='Frequency', unit='hertz', readLevel=3, **kw)
    add_results_options(out, confdb, with_errors=False)
    return out

# Select value from the best FlashLine data source


def best(cdv, *opts):
    for opt in opts:
        val = cdv.values[opt]
        if val != 0:
            return val
    return 0


cdv_names = (('temperature', lambda cdv: cdv.furnace_temp),
             ('halftime', lambda cdv: cdv.t_half),
             ('parker', lambda cdv: best(cdv,
                                         'mat_parker_diff_ver_a',
                                         'mat_parker_diff',
                                         'calc_parker')),
             ('koski', lambda cdv: cdv.values['calc_koski']),
             ('heckman', lambda cdv: cdv.values['calc_heckman']),
             ('cowan5', lambda cdv: cdv.values['calc_cowan_5']),
             ('cowan10', lambda cdv: cdv.values['calc_cowan_10']),
             ('clarkTaylor', lambda cdv: best(cdv,
                                              'mat_clarktaylor_diff_ver_a',
                                              'mat_clarktaylor_diff',
                                              'calc_clark_and_taylor_avg')),
             ('clarkTaylor1', lambda cdv: cdv.values[
              'calc_clark_and_taylor_r1']),
             ('clarkTaylor2', lambda cdv: cdv.values[
              'calc_clark_and_taylor_r2']),
             ('clarkTaylor3', lambda cdv: cdv.values[
              'calc_clark_and_taylor_r3']),
             ('degiovanni', lambda cdv: best(cdv,
                                             'mat_degio_diff_ver_a',
                                             'mat_degio_diff',
                                             'calc_degiovanni')),
             )


def assign_cdv_to_shot(shot, cdv, line):
    for i, (key, func) in enumerate(cdv_names):
        shot[key] = float(func(cdv))
    shot['stable'] = bool(line[-1])

def assign_cdt_to_shot(shot, cdt):
    if not cdt:
        return False
    shot['laserSetpoint'] = float(cdt.Laser)
    shot['laserPower'] = float(cdt.Laser_other[0])
    return True

def get_sample_segment(sample, segment=0):
    """Search for number `segment` in `sample` object children."""
    for child in sample.devices:
        if not child.has_key('segment'):
            continue
        elif child['segment'] == segment:
            return child
    logging.error('Sample segment not found!', sample.list(), segment)
    return False


def fill_results(sample, results, shots, additional_temp_values=[]):
    """Fills `sample` object with `results`."""
    shot = -1
    segment = -1
    T_obj = None

    for line in results:
        line = line.astype('float64')
        sg = int(line[0])
        # Reset shot number at segment change
        if sg != segment:
            # Get new segment object
            segment = sg
            T_obj = get_sample_segment(sample, segment)
            shot = 0
        else:
            # Segment is not changing: increment shot number
            shot += 1
        if T_obj is False:
            logging.error(
                'Missing data files for sample segment:', sample['devpath'], segment)
            continue
        # Get the shot object
        N_obj = getattr(T_obj, 'N{}'.format(shot + 1))
        assign_cdv_to_shot(N_obj, shots[segment][shot]['cdv'], line)
        assign_cdt_to_shot(N_obj, shots[segment][shot]['cdt'])
        additional_temp_values.append([N_obj['time'], N_obj['temperature']])
        # Accumulate values for equilibrium averages

    return True


def cleanup(func):
    def wrapped_cleanup(self, *a, **k):
        try:
            ret = func(self, *a, **k)
        except:
            if self.outFile:
                self.outFile.close()
            raise
        finally:
            self.pool.terminate()
        return ret
    return wrapped_cleanup


def get_test_xml_path(path):
    if path.endswith('TestInformation.xml'):
        return path, False
    if os.path.isdir(path):
        fn = os.path.join(path, 'TestInformation.xml')
        if os.path.exists(fn):
            return fn, False
        return False, False
        
    smp_dir = os.path.dirname(path)
    test_dir = os.path.dirname(smp_dir)
    out = os.path.join(test_dir, 'TestInformation.xml')
    dia = False
    # Create diagnostic xml
    if not os.path.exists(out):
        out = os.path.join(smp_dir, 'TestInformation.xml')
        open(out, 'w').write(diagnostic.TestInformation)
        dia = True
    return out, dia


def create_heating_cycle(cycle_dict, t0):
    # Heating cycle definition
    if not len(cycle_dict):
        return [[0, 0]]
    cycle = sorted(cycle_dict.items(), key=lambda g: g[0])
    #t0 = cycle[0][0]
    cycle = list([(q[0] - t0).total_seconds(), q[1]] for q in cycle)
    flat = []
    for t, s in cycle:
        if len(flat) == 0:
            flat.append([t, s])
            continue
        # Extend previous segment duration
        if len(flat) > 1 and s == flat[-2][1] and s == flat[-1][1]:
            flat[-1][0] = t
            continue
        flat.append([t, s])

    cycle = [[0, 0]] + flat
    return cycle


def add_preferred_models(measure):
    measure.add_option('model', 'Chooser', False, 'Preferred FlashLine Model',
                       options=['User preference', 'Clark & Taylor', 'Degiovanni',
                                'Parker', 'Koski', 'Cowan', 'Heckman'],
                       values=[False, 'clarkTaylor',     'degiovanni', 'parker', 'koski', 'cowan5', 'heckman'])
    measure.add_option('fitting', 'Chooser', False,
                       'Preferred Curve-Fitting Model',
                       options=[
                           'User preference', 'Gembarovic 2D', 'In-Plane', 'Two Layers', 'Three Layers'],
                       values=[False, 'Gembarovic2D', 'InPlane', 'TwoLayers', 'ThreeLayers'])


def create_shot_datasets(shot_data, shot_obj, freq, cycle):
    """Prepare signal and laser datasets"""
    duration = 0
    out = {}
    for key, col in [('fw0', 'raw'), ('fw1', 'laser')]:
        data_header = shot_data.get(key, None)
        if data_header is None:
            logging.debug('Skipping shot dataset, no header:', key, col)
            continue
        data = dataparser.channel_data(data_header['_import_filename'])
        
        opt = shot_obj.gete(col)
        # Remove the last points as they frequently are==0
        remove_last_zeros = 3
        data = data[:-remove_last_zeros]
        
        if col=='raw':
            timecol = np.arange(len(data)) / freq
            
        duration = (len(data)-1)/freq
        
        out[col] = [data, opt, timecol]

        t = data_header['datetime']
        cycle[t] = data_header['setpoint']
        
    if len(out) == 2:
        # Run implicit baseline and save result
        try:
            timecol, data, laser_fit, raw, laser = _run_baseline_on_proxy(shot_obj,
                                               timecol,
                                               out['raw'][0],
                                               out['laser'][0])
        except:
            logging.error('create_shot_datasets', shot_obj['fullpath'], format_exc())
        duration = timecol[-1]
        out['raw'][0] = raw
        out['laser'][0] = laser
        # Translated time datasets
        out['raw'][-1] = timecol
        out['laser'][-1] = timecol
        
        out['corrected'] = [data, 
                            shot_obj.gete('corrected'), 
                            timecol]
        
        if laser_fit is not False:
            out['laserFit'] = [laser_fit, 
                               shot_obj.gete('laserFit'), 
                               timecol]
        
    shot_obj['duration'] = duration
    return shot_obj, out


class FakeResult(object):
    def __init__(self, res):
        self.res = res

    def get(self, *a, **k):
        return self.res


class FakePool(object):
    _processes = 1
    def apply_async(self, f, a, callback=lambda *a: 1):
        res = f(*a)
        callback(res)
        return FakeResult(res)

    def terminate(self):
        pass
    
    def close(self):
        pass
    
    def join(self):
        pass

def find_node_child(node, target):
    for k in node._children.keys():
        if k==target:
            node = node.get(k)
            break
    return node



class Converter(dataimport.Converter):
    file_pattern = '*TestInformation.xml;*.fw[0-9]'
    name = 'FlashLine test'
    pid = 'FlashLine data import'
    db = False
    tree = False
    diagnostic = False

    def __init__(self, *a, **k):
        dataimport.Converter.__init__(self, *a, **k)
        self.pool = multiprocessing.Pool()
        #self.pool = FakePool()
        self.pool_jobs = []
        
    @classmethod
    def check_importable(cls, filename):
        if get_test_xml_path(filename)[0]:
            return True
        return False

    def post_open_file(self, navigator, prefix='0:'):
        if self.original_input_file == self.test_information_xml:
            self.log.debug('post_open_file: nothing to do',
                          self.original_input_file)
            return False
        #if self.diagnostic:
        #    done = navigator.domain_double_clicked(node)
        #    return done
        shot = os.path.basename(self.original_input_file)
        self.log.debug('post_open_file', shot)
        sample, segment, shot = dataparser.decode_name(shot)
        path = prefix + 'flash/sample{}'.format(sample+1)
        node = navigator.model().tree.traverse(path)
        node = node.get(node._children.keys()[segment])
        node = find_node_child(node, 'N{}'.format(shot+1))
        #node = node.get(node._children.keys()[shot])
        self.log.debug('post_open_file: ', node.path, sample, segment, shot, node)
        done = navigator.domain_double_clicked(node)
        return done

    def write_shot_datasets(self, tree, shot_obj, creation_output, jcount, job):
        for key, (data, opt, timecol) in creation_output.iteritems():
            node_path = '/summary' + shot_obj['fullpath']
            timeinfo = (timecol[0], timecol[1] - timecol[0])
            dataimport.create_dataset(
                self.outFile, node_path, opt,
                data,
                timeinfo, cls=reference.FixedTimeArray)
        # Overwrite outdated shot object
        old_shot_obj = tree.toPath(shot_obj['fullpath'])
        segment_obj = old_shot_obj.parent()
        segment_obj.add_child(
            shot_obj['devpath'], shot_obj.desc, overwrite=True)
        job(jcount, self.pid, 'Shot data:' + shot_obj['fullpath'])
        return tree

    def process_pool_results(self, tree, jcount, job):
        """Collect results from pool and write them out to the HDF and back in the configuration tree"""
        self.jcount = 0
        self.concurrent = multiprocessing.Value('i')

        def callback(res):
            self.concurrent.value -= 1
            for i in range(self.pool._processes - self.concurrent.value):
                send_job()
            shot_obj, creation_output = res
            print('pool callback',shot_obj['fullpath'])
            self.write_shot_datasets(
                tree, shot_obj, creation_output, self.jcount, job)
            self.jcount += 1

        def send_job():
            if not len(self.pool_jobs):
                logging.debug('send_job: finished')
                return False
            func, args = self.pool_jobs.pop(0)
            logging.debug('send_job:',len(self.pool_jobs))
            self.pool.apply_async(func, args, callback=callback)
            self.concurrent.value += 1
            return True

        # Initialize pool
        for p in range(self.pool._processes):
            send_job()

        # Wait for jobs to end
        # concurrent never drops to 0 on windows
        while len(self.pool_jobs) > 0:
            print('Waiting for pool jobs', len(self.pool_jobs), self.concurrent.value)
            sleep(1)
        self.pool.close()
        self.pool.join()
        return self.jcount

    def create_results_datasets(self, obj):
        """Transfer diffusivity Table options into datasets."""
        for column, func in cdv_names[1:]:
            node_path = '/summary{}'.format(obj['fullpath'])
            self.log.debug('Creating results datasets', node_path, column)
            opt = deepcopy(obj.gete(column + 's'))
            tab = opt['current']
            print 'TABLE', column, tab
            tab = np.array(tab[1:]).transpose()
            tab[np.equal(tab, None)] = np.nan
            tab = tab.astype('float64')
            if not len(tab):
                self.log('Result table is empty', node_path)
                continue
            data_idx = 2
            error_idx = 3
            if opt['aggregate'] == 'table_flat':
                # Skip flattened columns from sub-aggregates
                n = len(opt['tree'][2]) - 1
                data_idx += n * 2
                error_idx += n * 3
            timecol = tab[0]
            opt['unit'] = opt['unit'][data_idx]
            dataimport.create_dataset(self.outFile, node_path, opt, 
                                      tab[data_idx], timecol)

            # Create the error dataset
            err = column + 'sError'
            if len(tab) < 4 or (err not in opt):
                self.log('No error column', err, obj['fullpath'])
                continue
            opt = obj.gete(err)
            dataimport.create_dataset(
                self.outFile, node_path, opt, tab[error_idx], timecol)

    def get_outpath(self, test_information_xml):
        self.original_input_file = test_information_xml
        test_information_xml, self.diagnostic = get_test_xml_path(test_information_xml)
        self.test_information_xml = test_information_xml
        info = dataparser.parameters(test_information_xml)
        if self.confdb.get('flash_importToDb', False):
            if os.path.exists(self.confdb['database']):
                self.db = self.confdb['database']
                dname = os.path.join(os.path.dirname(self.db), 'flash')
                if not os.path.exists(dname):
                    os.makedirs(dname)
        else:
            dname = os.path.dirname(test_information_xml)
        # Ensure output name uniqueness
        tid = info['TestID']['__data__'][0]
        fname = tid + '.h5'
        outpath = os.path.join(dname, fname)
        self.outpath = outpath
        self.info = info
        return outpath

    def create_debug_data(self, debug_data, tree, additional_temp_values, jcount=0, job=lambda *a: 1):
        self.log.debug('debug_data type in create', len(debug_data))
        if not len(debug_data):
            self.log.warning('Faking debug table')
            debug_data = fake_debug_table(z=self.zerotime)
        # Diagnostic table
        timecol = debug_data[d_t.f_time].astype('float64')
        # Remove duplicates
        timecol, idx = np.unique(timecol, return_index=True)
        timecol -= self.zerotime
        elapsed = timecol[-1]
        data = debug_data[d_t.f_goal_setpoint][idx].astype('float64')
        dataimport.create_dataset(
            self.outFile, '/summary/kiln', tree.kiln.gete('S'), data, timecol)
        jcount += 1
        job(jcount, self.pid, 'Setpoint curve')
        data = debug_data[d_t.f_P][idx].astype('float64')
        dataimport.create_dataset(
            self.outFile, '/summary/kiln', tree.kiln.gete('P'), data, timecol)
        jcount += 1
        job(jcount, self.pid, 'Power curve')

        # Insert additional_temp_values coming from shot measurements
        # into temperature dataset and timecol
        
        data = debug_data[d_t.f_Ts][idx].astype('float64')
        if additional_temp_values:
            # Sort by time
            self.log.debug('Additional temperature values', additional_temp_values)
            additional_temp_values.sort(key=lambda el: el[0])
            newtimes, newtemps = np.array(additional_temp_values).transpose()
            newtimes = np.concatenate((timecol, newtimes))
            newtemps = np.concatenate((data, newtemps))
            idx = np.argsort(newtimes)
            newtimes = newtimes[idx]
            newtemps = newtemps[idx]
            func = interp1d(newtimes, newtemps)
            newtimes = np.arange(int(newtimes[0]) + 1, int(newtimes[-1]) - 1)
            newtemps = func(newtimes)
        else:
            newtemps = data
            newtimes = timecol
        dataimport.create_dataset(
            self.outFile, '/summary/kiln', tree.kiln.gete('T'), newtemps, newtimes)
        jcount += 1
        job(jcount, self.pid, 'Temperature curve')
#         data = debug_data[d_t.f_Tk].astype('float64')
#         dataimport.create_dataset(outFile, '/summary/kiln', tree.kiln.gete('Tk'), data, timecol)
        
        # Create log table
        log_opt = ao({}, 'log', 'Log')['log']
        self.flash_log_ref = reference.Log(self.outFile, '/flash', log_opt)
        has_logs = debug_data[d_t.f_log]!='NoLog'
        self.log_t = debug_data[d_t.f_time, :][has_logs].astype('float64')-self.zerotime
        self.log_msg = debug_data[d_t.f_log, :][has_logs]
        
        self.log.debug('Parsed .d_t log messages', len(self.log_t))
        self.write_flash_logs()
        self.log('Converted Points')
        return jcount, elapsed
    
    def write_flash_logs(self):
        dta = os.path.join(os.path.dirname(self.test_information_xml), 'dta', '')
        
        vt, vmsg = parse_all_logs(dta)
        if len(vt):
            vt -= self.zerotime
            self.log_t = np.concatenate((self.log_t, vt))
            self.log_msg = np.concatenate((self.log_msg, vmsg))
            m = np.argsort(self.log_t)
            self.log_t = self.log_t[m]
            self.log_msg = self.log_msg[m]
        log = [(t, (10, self.log_msg[i])) for i, t in enumerate(self.log_t)]
        self.flash_log_ref.commit(log)

    def parse_sample_data(self, instrobj, n, test_data, zerotime):
        sample_data = dataparser.get_sample_data(self.info, n)
        segments, shots, results_table = sample_data
        test_data.append(sample_data)
        samples_info = self.info['AllSamplesInformation']['SampleInformation']
        smpidx = 'sample' + str(n + 1)
        smp = instrobj.add_child(smpidx, smp_tree(self.confdb))
        for config in [('name', 'SampleTitle'), ('fileID', 'SampleFileID'),
                       ('thickness', 'Thickness'),
                       ('diameter', 'Diameter'),
                       ('weight', 'Weight'),
                       ('specificHeatFile', 'SpecificHeatReferenceFile'),
                       ('densityFile', 'DensityFile'),
                       ('testType', 'SampleTestType'),
                       ('expansionType', 'ExpansionType'),
                       ('laserGeometry', 'CapsuleTitle'),
                       ('capsuleFileName', 'CapsuleFileName'),
                       ('viewedOuter', 'ViewedRadius'),
                       ('irradiatedInner', 'IrradiatedRadiusInner'),
                       ('irradiatedOuter', 'IrradiatedRadiusOuter'),
                       ]:
            name, xml_name = config
            data = samples_info[xml_name]['__data__']
            if len(data) < n + 1:
                self.log.error(
                    'Cannot find TestInformation.xml property', name, xml_name)
                continue
            smp.coerce(name, data[n])
            # Convert to diameters
            if name in ('viewedOuter', 'irradiatedInner', 'irradiatedOuter'):
                smp[name] *= 2 
                smp.setattr(name, 'precision', 4)
        
        duplicates = collections.defaultdict(lambda: -1)
        for sg in shots.keys():
            setpoint = segments.get(sg, None)
            if setpoint is None:
                self.log.warning('Skipping empty segment', sg)
                continue
            S = int(setpoint)
            duplicates[S]+=1
            spidx = 'T{}'.format(S)
            if duplicates[S]>0:
                spidx += '_{}'.format(duplicates[S])
            segment_obj = smp.add_child(spidx, equi_dict(self.confdb))
            segment_obj['setpoint'] = setpoint
            segment_obj['name'] += str(int(setpoint))
            if duplicates[S]>0:
                segment_obj['name'] += ' ({})'.format(duplicates[S])
            segment_obj['shots'] = len(shots[sg])
            segment_obj['segment'] = sg
            
            for shot in shots[sg].keys():
                header = shots[sg][shot]['header']
                sh = 'N' + str(shot + 1)
                shot_obj = segment_obj.add_child(sh, shot_dict(self.confdb))
                shot_obj['setpoint'] = header['setpoint']
                # Will be fixed by fill_results
                shot_obj['temperature'] = header['temperature']
                # Not reliable!
                #if shots[sg][shot]['cdv']:
                #    shot_obj['time'] = shots[sg][shot]['cdv'].eval_time - zerotime
                #    self.log.debug( 'Shot time cdv', shot_obj['fullpath'], shot_obj['time'], shots[sg][shot]['cdv'].eval_time, zerotime)
                #else:
                shot_obj['time'] = (header['datetime'] - self.zerodatetime).total_seconds()
                self.log.debug('Shot time header', shot_obj['fullpath'], shot_obj['time'], header['datetime'], self.zerodatetime)
                shot_obj['frequency'] = header['frequency']

    @cleanup
    def convert(self, test_information_xml, jobs=lambda *a: 1, job=lambda *a: 1, done=lambda *a: 1):
        """Extract a FlashLine test and export into a Misura test file"""
        global clogging
        clogging = self.log
        self.original_input_file = test_information_xml
        test_information_xml, self.diagnostic = get_test_xml_path(test_information_xml)
        self.test_information_xml = test_information_xml
        outpath = self.outpath
        if not outpath:
            outpath = self.get_outpath(test_information_xml)
        if not outpath:
            self.log.error('Aborting conversion: No outpath')
            return False
        info = self.info
        nSamples = int(
            info['AllSamplesInformation']['NumberSamples']['__data__'][0])
        jobs(5 + nSamples, self.pid)
        job(1, self.pid, 'Parsed XML information')
        outFile = indexer.SharedFile(outpath, mode='w')
        self.outFile = outFile
        job(2, self.pid, 'Opened output file: ' + outpath)
        instr = 'flash'
        # Create instrument dict
        tree = dataimport.tree_dict()
        tree[instr] = dataimport.instr_tree()
        self.log('Importing from', test_information_xml)
        self.log('Conversion Started at ', datetime.now().strftime("%H:%M:%S, %d/%m/%Y"))
        
        # READ DATA
        debug_data, zerodatetime = dataparser.get_debug_data(info)
        self.log.debug('debug_data type in coverter', type(debug_data))
        # Times
        dd = info['DateData']
        zerotime = float(dd['TimeInSeconds']['__data__'][0])
        self.zerotime = zerotime
        tdate0 = localtime(zerotime)
        tdate = strftime("%H:%M:%S, %d/%m/%Y", tdate0)
        if not zerodatetime:
            zerodatetime = datetime.fromtimestamp(mktime(tdate0))
        self.zerodatetime = zerodatetime
        # Get a configuration proxy
        tree = option.ConfigurationProxy(tree)
        tree._readLevel = 5
        tree._writeLevel = 5
        tree['runningInstrument'] = instr
        tree['lastInstrument'] = instr
        
        instrobj = getattr(tree, instr)
        instrobj['mro'] = ['Flash','Instrument']
        instrobj['name'] = get_data(info, ['InstrumentName'], 0, 'Flash')
        instrobj['nSamples'] = nSamples
        
        # Measure
        instrobj.measure['mro'] = ['MeasureFlash','Measure']
        instrobj.measure['nSamples'] = nSamples
        instrobj.measure['operator'] = get_data(
            info, ['Operator'], 0, 'unknown')
        tid = info['TestID']['__data__'][0]
        instrobj.measure['name'] = tid
        instrobj.measure['comment'] = get_data(
            info, ['TestTitle'], 0, 'TestInformation')
        instrobj.measure.setattr('name', 'name', 'Test ID')
        instrobj.measure.setattr('comment', 'name', 'Test Title')
        instrobj.measure['date'] = tdate
        instrobj.measure['id'] = tid
        instrobj.measure.setattr('id', 'name', 'Test ID')
        uid = info['uid']
        instrobj.measure['uid'] = uid
        instrobj.measure['zerotime'] = zerotime
        add_preferred_models(instrobj.measure)
        instrobj['zerotime'] = zerotime

        # Parse sample data from xml and insert into conf
        test_data = []
        jcount = 3
        for n in range(nSamples):
            jcount += 1
            job(jcount, self.pid, 'Parsing sample data: {}'.format(n+1))
            self.parse_sample_data(instrobj, n, test_data, zerotime)
            
            
        # Fill-in reference data values (also diffusivity etc)
        calc_reference_data(tree)
        # Create the datasets hierarchy
        dataimport.create_tree(outFile, tree)
        
        job(jcount + 1, self.pid, 'Created the datasets hierarchy')

        # Reset jobs counter: one job x shot+one per sample+one per segment+4
        j = 4+nSamples
        for n in range(nSamples):
            for segment in test_data[n][1].keys():
                j += 1 # one x segment
                j += len(test_data[n][1][segment]) # one x shot
        jobs(j, self.pid)
        jcount = 0
        # ##
        # GET THE SHOT DATA
        cycle = {}
        add_temp_values = []
        sample_objects = []
        segment_objects = []
        for n in range(nSamples):
            smpobj = getattr(instrobj, 'sample' + str(n + 1))
            sample_objects.append(smpobj)
            segments, shots, results_table = test_data[n]
            if len(segments) == 0:
                self.log.error('Missing sample data for sample', n)
                continue
            if results_table is not None:
                fill_results(smpobj, results_table, shots, add_temp_values)
            
            duplicates = collections.defaultdict(lambda: -1)
            for sg in shots.keys():
                S = int(segments.get(sg, None))
                if S is  None:
                    self.log.warning('Skipping empty segment', sg)
                    continue
                duplicates[S] += 1
                segment_name = 'T{}'.format((S))
                if duplicates[S]>0:
                    segment_name += '_{}'.format(duplicates[S])
                segment_obj = getattr(smpobj, segment_name)
                segment_objects.append(segment_obj)
                for shot in shots[sg].keys():
                    if self.interrupt:
                        self.cancel()
                        return False
                    shot_name = 'N' + str(shot + 1)
                    shot_obj = getattr(segment_obj, shot_name)
                    shot_data = shots[sg][shot]
                    freq = shot_obj['frequency']
                    self.pool_jobs.append((create_shot_datasets, (shot_data, shot_obj,
                                                                  freq, cycle)))
            
        # Wait for all results to be processed
        jcount = self.process_pool_results(tree, jcount, job)
        # Update aggregates and create results datasets
        for segment_obj in segment_objects:
            jcount += 1
            job(jcount, self.pid, 'Processing segment results '+ segment_obj['fullpath'])
            segment_obj.update_aggregates(recursive=False)
            self.create_results_datasets(segment_obj)
        for smpobj in sample_objects:
            jcount += 1
            job(jcount, self.pid, 'Processing sample results '+ segment_obj['fullpath'])
            smpobj.update_aggregates(recursive=False)
            self.create_results_datasets(smpobj)

        # Add the grand summary table
        add_merge_tables(instrobj)
        # Mirror the instrument summary table so it is visible in measure panel
        instrobj.measure.add_option('summary', 'RoleIO', name='Summary', options=[
                                    '/flash/', 'default', 'summary'])
        instrobj.update_aggregates(recursive=False)

        outFile.flush()

        tree.kiln['curve'] = create_heating_cycle(cycle, zerodatetime)

        jcount, elapsed = self.create_debug_data(
            debug_data, tree, add_temp_values, jcount, job)

        ######
        # Final configuration adjustment and writeout
        ######
        instrobj.measure['elapsed'] = elapsed

        # Write conf tree
        outFile.save_conf(tree.tree())
        outFile.set_attributes('/conf', attrs={'version': '3.0.0',
                                               'zerotime': zerotime,
                                               'elapsed': elapsed,
                                               'instrument': instr,
                                               'date': tdate,
                                               'serial': info['InstrumentName']['__data__'][0],
                                               'uid': uid})
        jcount += 1
        job(jcount, self.pid, 'Wrote conf tree and general attributes')
        self.log('Conversion ended.')
        outFile.header(refresh=True)
        outFile.close()
        if self.db:
            indexer.Indexer.append_file_to_database(self.db, self.outpath)
        done(self.pid)
        self.tree = tree
        return self.outpath

try:
    from thegram.model.baseline import _run_baseline_on_proxy
    dataimport.data_importers.add(Converter)
except:
    logging.debug('Cannot find a valid baseline model. FlashLine import is disabled.')
    from traceback import print_exc
    print_exc()


