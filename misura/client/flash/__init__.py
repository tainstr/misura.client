#!/usr/bin/python
# -*- coding: utf-8 -*-
from traceback import print_exc
from . import flashline
from . import reference_files


# Additional configuration options
from misura.canon.option import ao, ConfigurationProxy
from misura.canon.plugin import clientconf_update_functions, default_plot_rules
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
try:
    from . import navigator
    from . import plugin
except:
    print('REQUIRES misura.client migration to py3')
    print_exc()

confdb = None

rule_test_plot = r'''flash/sample[0-9]+/XmodelXs$
flash/sample[0-9]+/XfittingX$
flash/sample[0-9]+/references$'''

# SampleX will be rewritten
rule_sample_plot = r'''flash/sampleX/XmodelXs$
flash/sampleX/XfittingX$
flash/sampleX/T(-)?[0-9]+(_[0-9]+)?/XmodelXs$
flash/sampleX/T(-)?[0-9]+(_[0-9]+)?/XfittingX$
flash/sampleX/references$'''

rule_segment_plot = r'''flash/sampleX/segmentX/N[0-9]+/corrected$'''
#flash/sampleX/segmentX/N[0-9]+/XfittingX/theory$'''

rule_shot_plot = r'''flash/sampleX/segmentX/shotX/raw$'''

rule_model_plot = r'''flash/sampleX/segmentX/shotX/raw$
flash/sampleX/segmentX/shotX/modelX/theory$'''

legacy_options=['Clark & Taylor', 'Degiovanni', 'Parker', 'Koski', 'Cowan', 'Heckman']
legacy_values=['clarkTaylor',     'degiovanni', 'parker', 'koski', 'cowan5','heckman']



load_reference_rule = r'flash/sample[0-9]+/references$'

model_rule = lambda model: r'^/flash/sample.*/{}(s|sError|Error|Ref)?$'.format(model)

def set_flash_model_visibility(conf, key, old, new):
    model = key.split('_')[-1]
    rule = model_rule(model)
    opt = conf['opt_hide']
    # Add new rule to hide the model
    if (not new) and (rule not in opt):
        if len(opt): rule = '\n'+rule
        conf['opt_hide']+=rule
    # Remove rule to show the model
    if new and rule in opt:
        nrule = '\n'+rule
        if nrule in opt:
            rule = nrule
        conf['opt_hide'] = opt.replace(rule, '')
    return new

def get_flash_model_visibility(conf, key, old, new):
    if not key.startswith('flash_en_'):
        return new    
    model = key.split('_')[-1]
    if model_rule(model) in conf['opt_hide']:
        return False
    return True
    
    
ConfigurationProxy.callbacks_set.add(set_flash_model_visibility)
ConfigurationProxy.callbacks_get.add(get_flash_model_visibility)

laser_geometry = [[('Title', 'String'), ('Irradiated Outer', 'Float'), 
                   ('Irradiated Inner', 'Float'), ('Viewed Outer', 'Float'), 
                   ('Viewed Inner', 'Float')],
            ['InPlane1 0.762', 2.0574, 0.762, 0.508, 0],
            ['InPlane2 1.112', 2.0574, 1.11252, 0.508, 0],
            ['InPlane3 1.43', 2.0574, 1.43, 0.508, 0],
            ['InPlane4 1.747', 2.0574, 1.74752, 0.508, 0],
    ]

def get_laser_geometry_name(new):
    if new=='__autoguess__':
        return [0.0]*5
    elif new=='':
        return False
    for v in confdb['flash_laser'][1:]:
        # Reset all to 0 for auto guess
        if v[0]!=new:
            continue
        return v
    return False
    
            
def list_laser_geometries(conf, key, old, new):
    if not confdb:
        logging.error('list_laser_geometries No confdb!')
        return new
    r = []
    for v in confdb['flash_laser'][1:]:
        r.append(v[0])
    conf.setattr(key, 'values', r+['__autoguess__',''])
    conf.setattr(key, 'options', r+['Auto Guess', 'Custom'])
    
    real = [conf[nkey] for nkey in ('irradiatedOuter', 'irradiatedInner', 
                                  'viewedOuter','viewedInner')]
    if sum(real)==0:
        # Auto-guess
        logging.debug('list_laser_geometries reset to auto-guess', real, old, repr(new))
        return '__autoguess__'
    
    theor = get_laser_geometry_name(new)
    
    if theor and real!=theor[1:]:
        logging.debug('Laser geometry mismatch for ', repr(old), repr(new))
        # Set to custom
        new = ''
    
    logging.debug('list_laser_geometries', repr(old), repr(new), real, theor, r)
    return new

def set_laser_geometry(conf, key, old, new):
    # Abort setting to custom
    if new == '':
        return new
    if not confdb:
        logging.error('set_laser_geometry No confdb!')
        return new
    from misura.client.live import registry
    v = get_laser_geometry_name(new)
    if not v:
        logging.debug('set_laser_geometry: not found', repr(new))
        return new
    for i, nkey in enumerate(('irradiatedOuter', 'irradiatedInner', 
                                  'viewedOuter','viewedInner')):
        conf[nkey] = v[i+1]
        registry.force_redraw([conf.getattr(nkey, 'kid')])
    return new

ConfigurationProxy.callbacks_set.add(set_laser_geometry)
ConfigurationProxy.callbacks_get.add(list_laser_geometries)

def add_thegram_options(confdb1):
    global confdb
    confdb = confdb1
    confdb.add_option('flash', 'Section', 'Flash', 'Flash')
    confdb.add_option(
        'flash_importToDb', 'Boolean', True, 'Import FlashLine to default database')
    confdb.add_option('flash_open', 'Chooser', 'Ask', 'Show on opening:', options=['Ask', 'Wizard','Plot'])
    confdb.add_option('flash_model', 'Chooser', 'clarkTaylor', 'Preferred FlashLine Model')
    confdb.setattr('flash_model', 'options', legacy_options[:])
    confdb.setattr('flash_model', 'values', legacy_values[:])
    if confdb['flash_model'] not in legacy_values:
        confdb['flash_model'] = 'clarkTaylor'
        
    kw = {'parent':'flash_model', 'callback_set':'set_flash_model_visibility',
          'callback_get':'get_flash_model_visibility'}
    en_default = 'flash_en_halftime' in confdb
    confdb.add_option('flash_en_halftime', 'Boolean', True, 'Enable HalfTime', **kw)
    confdb.add_option('flash_en_clarkTaylor', 'Boolean', True, 'Enable Clar&Taylor', **kw)
    confdb.add_option('flash_en_clarkTaylor1', 'Boolean', True, 'Enable Clar&Taylor 1', **kw)
    confdb.add_option('flash_en_clarkTaylor2', 'Boolean', True, 'Enable Clar&Taylor 2', **kw)
    confdb.add_option('flash_en_clarkTaylor3', 'Boolean', True, 'Enable Clar&Taylor 3', **kw)
    confdb.add_option('flash_en_parker', 'Boolean', True, 'Enable Parker', **kw)
    confdb.add_option('flash_en_degiovanni', 'Boolean', True, 'Enable Degiovanni', **kw)
    confdb.add_option('flash_en_koski', 'Boolean', True, 'Enable Koski', **kw)
    confdb.add_option('flash_en_cowan5', 'Boolean', True, 'Enable Cowan 5', **kw)
    confdb.add_option('flash_en_cowan10', 'Boolean', True, 'Enable Cowan 10', **kw)
    confdb.add_option('flash_en_heckman', 'Boolean', True, 'Enable Heckman', **kw)
    
    # Hide
    if not en_default: 
        for h in 'clarkTaylor,halftime'.split(','):
            confdb['flash_en_'+h]=True
        for h in 'clarkTaylor1,clarkTaylor2,clarkTaylor3,parker,degiovanni,koski,cowan5,cowan10,heckman'.split(','):
            confdb['flash_en_'+h]=False
    
    confdb.add_option('flash_fitting', 'Chooser', 'gembarovic',
                      'Preferred Curve-Fitting Model')
    confdb.setattr('flash_fitting', 'options', ['None', 'Gembarovic 2D', 'In-Plane', 'Two Layers', 'Three Layers'])
    values = ['', 'Gembarovic2D', 'InPlane', 'TwoLayers','ThreeLayers']
    confdb.setattr('flash_fitting', 'values', values)
    if confdb['flash_fitting'] not in values:
        confdb['flash_fitting'] = ''
    
    confdb.add_option(
        'flash_jg2d_halfTimes', 'Integer', 8, 'N HalfTimes, Gembarovic')
    confdb.add_option(
        'flash_inpl_halfTimes', 'Integer', 20, 'N HalfTimes, InPlane')
    confdb.add_option(
        'flash_ml2_halfTimes', 'Integer', 8, 'N HalfTimes, 2 Layers')
    confdb.add_option(
        'flash_ml3_halfTimes', 'Integer', 8, 'N HalfTimes, 3 Layers')
    confdb.add_option(
        'flash_centerGravity', 'Boolean', True, 'Use Center of Gravity to detect initial time')
    

    ############
    # Model guess
    confdb.add_option('flash_guess_jg2d', 'Chooser', 'clarkTaylor', 'Initial Gembarovic guess', 
                      options=legacy_options[:],
                      values=legacy_values[:])
    confdb.add_option('flash_guess_inpl', 'Chooser', 'clarkTaylor', 'Initial In-Plane guess', 
                      options=legacy_options[:],
                      values=legacy_values[:])
    confdb.add_option('flash_guess_ml2', 'Chooser', 'clarkTaylor', 'Initial Two-Layers guess', 
                      options=legacy_options[:],
                      values=legacy_values[:])
    confdb.add_option('flash_guess_ml3', 'Chooser', 'clarkTaylor', 'Initial Three-Layers guess', 
                      options=legacy_options[:],
                      values=legacy_values[:])
    
    ##########
    # Laser geometries
    confdb.add_option('flash_laser', 'Table', laser_geometry, 'Laser geometries', precision=['None',4,4,4,4])

    #######################    
    # Plotting options
    confdb.add_option(
        'flash_plotHalfTimes', 'Integer', 20, 'Show HalfTime multiple on thermograms', min=0)
    confdb.add_option(
        'flash_test_plot', 'TextArea', rule_test_plot, 'Flash Test plot rule')
    # Upgrade
    if 'XmodelX' not in confdb['flash_test_plot']:
        confdb['flash_test_plot'] = rule_test_plot
    
    confdb.add_option(
        'flash_sample_plot', 'TextArea', rule_sample_plot, 'Flash Sample plot rule')

    if '/T[0-9]+/' in confdb['flash_sample_plot']:
        confdb['flash_sample_plot'] = confdb['flash_sample_plot'].replace('/T[0-9]+/', '/T(-)?[0-9]+(_[0-9]+)?/')
    confdb.add_option(
        'flash_segment_plot', 'TextArea', rule_segment_plot, 'Flash Segment plot rule')
    confdb.add_option(
        'flash_shot_plot', 'TextArea', rule_shot_plot, 'Flash Shot plot rule')
    confdb.add_option(
        'flash_model_plot', 'TextArea', rule_model_plot, 'Model fitting plot rule')
    
    return True

def generate_default_plot_rule(confdb, conf=False):
    """Generate a load/plot rule from configuration db and local test file configuration"""
    measure = False
    if conf: 
        if not conf['runningInstrument']=='flash':
            return False
        measure =  conf.flash.measure
    rule = navigator.domains.replace_models(confdb['flash_test_plot'], measure)
    logging.debug('generate_default_plot_rule', repr(confdb['flash_test_plot']), repr(rule))
    return rule


clientconf_update_functions.append(add_thegram_options)
default_plot_rules['flash'] = generate_default_plot_rule


import os
import sys


def determine_path(root=__file__):
    """Borrowed from wxglade.py"""
    try:
        #       root = __file__
        if os.path.islink(root):
            root = os.path.realpath(root)
        return os.path.dirname(os.path.abspath(root))
    except:
        print("I'm sorry, but something is wrong.")
        print("There is no __file__ variable. Please contact the author.")
        sys.exit()

flashdir = determine_path()  # Executable path
