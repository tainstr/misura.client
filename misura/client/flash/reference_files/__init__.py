# -*- coding: utf-8 -*-
"""FlashLine reference files parsing"""
import os
from traceback import format_exc, print_exc

import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline

from misura.canon import determine_path
from misura.canon.logger import get_module_logging
from misura.canon.option import ConfigurationProxy


logging = get_module_logging(__name__)
folder = determine_path(__file__)

# Types: 1=specheat, 2=density, 3=diffusivity, 4=expansion, 5=general


def reference_file(filepath):
    """Reads reference file in filepath and returns a dictionary of parsed data"""
    dat = open(filepath, 'r').read().splitlines()
    out = {'name': os.path.basename(filepath)}
    out['title'] = dat[0].strip()
    out['version'] = dat[1].strip()
    out['typecode'] = int(dat[2][:3].replace(' ', ''))
    if out['typecode'] != int(out['name'].split('.')[-1][2:]):
        logging.error(
            'Reference type and name mismatch', out['typecode'], out['title'])
    if '(' in dat[2]:
        n, u = dat[2][3:].split(' (')
    else:
        n = dat[2][3:].strip()
        u = ''
    out['typename'] = n.replace(' ', '')
    out['unit'] = u[:-1]

    def fval(line): return float(line.split(';')[0].replace(' ', ''))
    out['Tmin'] = fval(dat[3])
    out['Tmax'] = fval(dat[4])
    out['Tmat'] = fval(dat[5])
    out['eq'] = int(fval(dat[6]))
    out['coeff'] = int(fval(dat[7]))

    def pval(line):
        line = line.replace(';', ' ').strip()
        while '  ' in line:
            line = line.replace('  ', ' ')
        line = line.replace(',', '.').split(' ')
        return [float(e) for e in line]
    vals = []
    for line in dat[8:]:
        if len(line) < 5:
            break
        vals.append(pval(line))
    out['values'] = vals
    if len(vals) != out['coeff']:
        logging.error(
            'Expected number of coefficient was not respected in', out['name'], len(vals), out['coeff'])
    return out


"""
       values=[0, 1, 2, 3, 4, 5, 10, 11, 25],
       options=['Quartic (°K) (A,B,C,D,E)',
                'A + (B*T²)*(sqrt( T )) + (C*T³) + (D/T²)',
                'A +B*t^2*sqrt(T) + C*(log(T)/T²) + D*(e^-T))',
                'A + (B/(t1*sqrt(T))) + ( C*e^-T))',
                'Fixed -909.0',
                'A + B*T + C*T² + D/T + E/T²',
                'Quartic (°C) (A,B,C,D,E)', 
                'Quadratic (A,B,C) if T<D; else Cubic (E,F,G,H)',
                'Linear interpolation'],
"""


class ReferenceFile(object):

    def __init__(self, filepath):

        if not os.path.exists(filepath):
            filepath = get_reference_file(filepath)
        self._data = reference_file(filepath)
        if not self._data:
            logging.error('Cannot parse a reference file!', filepath)
            raise
        self._filepath = filepath
        self._equations = {0: self._quartic_Kelvin,
                           4: self._fixed_909,
                           10: self._quartic,
                           11: self._quadratic_or_cubic,
                           25: self._linear_interpolation, }

    def __getattr__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        elif key in dir(self):
            return object.__getattribute__(self, key)
        return self._data[key]

    def __call__(self, x):
        return float(self._equations[self.eq](x))

    @property
    def _xy(self):
        return np.array(self.values).transpose()

    _func_linear_interpolation = False

    def _quartic_Kelvin(self, T):
        self._quintic(T + 273.)

    def _fixed_909(self, T):
        return -909

    def _poly(self, degree, T):
        fac = [e[0] for e in self.values]
        # Cut down number of factors
        if len(fac) > degree:
            fac = fac[:degree]
        # Highest degree comes first
        return np.polyval(fac[::-1], T)

    def _quartic(self, T):
        return self._poly(5, T)

    def _quadratic_or_cubic(self, T):
        if T < self.values[3][0]:
            return self._poly(3, T)
        else:
            return self._poly(4, T)

    def _linear_interpolation(self, x):
        # Check out of margin
        if x < self.Tmin:
            return self.values[0][1]
        elif x > self.Tmax:
            return self.values[-1][1]
        if self._func_linear_interpolation is False:
            # Interpolate
            self._func_linear_interpolation = InterpolatedUnivariateSpline(
                *self._xy, k=1)
        return self._func_linear_interpolation(x)

    # TODO: implement all equation types as defined by FlashLine


def list_reference_files(reference_type=-1):
    r = os.listdir(folder)
    if reference_type < 0:
        return ['None'] + filter(lambda e: e[-4:-1] == '.rf', r)
    ext = '.rf{}'.format(reference_type)
    r = ['None'] + filter(lambda e: e.endswith(ext), r)
    logging.debug('list_reference_files', r)
    return r


def guess_reference_file_name(original_filename):
    return original_filename.replace('\\', '/').split('/')[-1].lower()


def get_reference_file(name):
    if name == 'None':
        return False
    r = os.path.join(folder, name.lower())
    if not os.path.exists(r):
        logging.debug('Reference file not found in ', r)
        return False
    return r


def iterate_result_handles():
    from ..flashline.convert import result_handles, ref_name
    from misura.client.clientconf import confdb
    for h0 in result_handles[1:] + [('jg2d_diffusivity', 'Gembarovic2D'),
                                ('inpl_diffusivity', 'InPlane'),
                                ('ml2_diffusivity2', 'TwoLayers'),
                                ('ml3_diffusivity3', 'ThreeLayers')]:
        h0, name = h0[:2]
        # non existent plugin model

        h = ref_name(h0)
        if not name:
            name = 'Diffusivity'
        en = 'flash_en_' + h0
        vis = True
        if en in confdb:
            vis = confdb[en]
        yield h0, h, name, vis


def add_segment_reference_errors(seg, refval=0):
    """Adds aggregate reference errors as % to segment"""
    for h0, h, name, vis in iterate_result_handles():
        if h0 not in seg:
            continue
        if refval is None:
            if h in seg:
                seg.delete(h)
            continue
        if  vis and (h not in seg):
            seg.add_option(h, 'Float', 0, 'Ref {}'.format(name), unit='percent', parent='reference',
                           aggregate='mean()', attr=['Result'])
        elif (h in seg) and (not vis):
            seg.delete(h)

def add_shot_reference_errors(shot, refval):
    """Adds reference errors as % to shot"""
        
    for h0, h, name, vis in iterate_result_handles():
        # non existent plugin model
        if h0 not in shot:
            continue
        if refval is None:
            if h in shot:
                shot.delete(h)
            continue
        # Initial value
        err = 100. * (shot[h0] - refval) / refval
        # Add a new option
        if vis and (h not in shot):
            shot.add_option(h, 'Float', err, 'Ref {}'.format(name), 
                            unit='percent', precision=4, 
                            aggregate='deviation({}, reference)'.format(h0),
                            parent='reference', attr=['ReadOnly', 'Result'])
        elif (h in shot) and (not vis):
            shot.delete(h)
            
    for model in shot.devices:
        add_shot_reference_errors(model, refval)
    
    # Recurse downward to models
    shot.update_aggregates(-1)


def calc_reference(shot, ref):
    if not shot.has_key('temperature'):
        logging.error('calc_reference: not a shot', shot['fullpath'])
        return False
    if ref is False:
        val = 0
    else:
        T = shot['temperature']
        val = ref(T)
    if 'reference' not in shot:
        shot.add_option('reference', 'Float', 0, 'Reference', precision=4, 
                        unit='cm^2/second', attr=['ReadOnly', 'Result'])
    shot['reference'] = val
    # TODO: 4% should be adjustable!
    shot.parent()['referenceError'] = val * 0.04
    add_shot_reference_errors(shot, val)
    logging.debug('Reference', val, shot['fullpath'])
    return True


def get_sample_reference(refname):
    ref = get_reference_file(refname)
    if not ref:
        logging.error('No reference file for sample', refname, ref)
        return False
    try:
        ref = ReferenceFile(ref)
    except:
        logging.error('Error parsing reference file', format_exc())
        return False
    return ref


def calc_reference_data_sample(smp, ref=False):
    """Calculate reference data options for sample `smp`"""
    i = 0
    # TODO: extend towards other files
    if ref is False:
        logging.debug('No reference file', smp['diffusivityFile'])
        smp.delete('references')
        smp.remove_aggregation_target('summary', 'reference')
        smp.remove_aggregation_target('summary', 'referenceError')
        for segment in smp.devices:
            segment.remove_aggregation_target('summary', 'reference')
            segment.delete('references')
            segment.delete('reference')
            segment.delete('referenceError')
            add_segment_reference_errors(segment, None)
            for shot in segment.devices:
                add_shot_reference_errors(shot, None)
                shot.delete('reference')
        smp.parent().update_aggregates(recursive=-1)
        return False
    smp.add_option('references', 'Table', [], 'Reference', attr=['ReadOnly', 'Result'], 
                   aggregate='table(time, temperature, reference, referenceError, setpoint)')
    smp.add_aggregation_target('summary', 'reference')
    smp.add_aggregation_target('summary', 'referenceError')
    for segment in smp.devices:
        segment.add_aggregation_target('summary', 'reference')
        segment.add_option('references', 'Table', [], 'Reference', attr=['ReadOnly', 'Result'], 
                   aggregate='table(time, temperature, reference)')
        segment.add_option('reference', 'Float', 0, 'Reference', unit='cm^2/second', precision=4,
                           aggregate='mean()', error='referenceError', attr=['ReadOnly', 'Result'])
        segment.add_option('referenceError', 'Float', 0, 'Reference Error', precision=8, attr=['ReadOnly', 'Result'],
                            aggregate='mean()', unit='cm^2/second', parent='reference')
        for shot in segment.devices:
            i += calc_reference(shot, ref)
        add_segment_reference_errors(segment)
    # Grand summary table
    smp.parent().update_aggregates(recursive=-1)
    return i


def calc_reference_data(conf):
    """Calculate reference data options for configuration proxy `conf`"""
    i = 0
    if not conf.has_child('flash'):
        logging.debug('Not applicable')
        return False
    logging.debug('calc_reference_data', conf.flash.samples)
    for smp in conf.flash.samples:
        ref = get_sample_reference(smp['diffusivityFile'])
        # TODO: extend towards other files
        i += calc_reference_data_sample(smp, ref)
    logging.debug('Added reference data to objects: ', i)
    return i


def _update_reference_diffusivity_callback(conf, key, old, new):
    ref = get_sample_reference(new)
    calc_reference_data_sample(conf, ref)
    logging.debug('Added reference data to sample: ', conf['fullpath'])

    return new


load_reference_rule = r'''flash/sample[0-9]+/references$'''


def update_reference_diffusivity(conf, key, old, new):
    # Update data
    new = _update_reference_diffusivity_callback(conf, key, old, new)
    if False in (conf.doc, conf.filename):
        logging.error('No document found!', conf.doc, conf.filename)
        return new
    r = conf.doc.load_rule(conf.filename, load_reference_rule, overwrite=False)
    logging.debug('loaded datasets', r)
    # Update datasets
    try:
        conf.doc.model.pause(True)
        from misura.client.filedata import generate_datasets
        generate_datasets.recurse_generate_datasets(
            conf, conf.doc, 'references')
    except:
        print_exc()
    conf.doc.model.pause(False)
    conf.doc.sigConfProxyModified.emit()
    return new


def list_reference_diffusivity(conf, key, old, new):
    opt = conf.gete(key)
    opt['options'] = list_reference_files(3)
    conf.sete(key, opt)
    return new


ConfigurationProxy.callbacks_set.add(update_reference_diffusivity)
ConfigurationProxy.callbacks_get.add(list_reference_diffusivity)
