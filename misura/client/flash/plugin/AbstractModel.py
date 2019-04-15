#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run a model in a veusz plugin"""
import os
from time import sleep
import threading
import tempfile
from pickle import dumps, loads
import numpy as np

from misura.canon.csutil import find_nearest_val
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from veusz import plugins
from misura.client import _
from misura.client.plugin import OperationWrapper, FieldMisuraNavigator
from misura.canon import option

from misura.client.filedata.generate_datasets import recurse_generate_datasets, new_dataset_operation, add_datasets_to_doc
from misura.client.clientconf import confdb

import Baseline
from ..model import parameters, shapefit
from ..model.parameters import fallback

from PyQt4 import QtGui

def populate_output_object(input_object, output_object, prefix='jg2d_'):
    """Called by AbstractFlashModelPlugin.post_process() to fill results."""
    for handle in input_object.keys():
        if not handle.startswith(prefix):
            continue
        if not output_object.has_key(handle):
            logging.debug('populate_output_object: missing destination', handle)
            continue
        output_object[handle] = input_object[handle]
        opt = input_object.gete(handle)
        if 'Result' in opt.get('attr',[]):
            # Set default to actual value 
            fd = input_object[handle]
        else:
            # Copy any original default
            fd = input_object.getattr(handle,'factory_default')
        output_object.setattr(handle, 'factory_default', fd)
    return output_object


def get_params(cfg, signal, t, pclass, prefix='jg2d_'):
    """Create Params instance.
    Called by AbstractFlashModelPlugin.load_datasets"""
    params = pclass()
    handle, params.filename = tempfile.mkstemp()
    os.close(handle)
    # Copy configurations from proxy to params
    params.read_configuration(cfg, prefix=prefix)

    # TODO: move these parts to a Params. method.
    # Correct start index by jumpPoints time (ms)
    if confdb['flash_centerGravity']:
        start_index = cfg['base_laserCenterIndex']
    else:
        start_index = cfg['base_laserStartIndex']
    t0 = t[start_index] + (cfg[prefix + 'jumpPoints'] / 1000.)
    start_index = find_nearest_val(t, t0, seed=start_index)
    # End time
    t1 = cfg[prefix + 'endTime'] / 1000.
    end_index = find_nearest_val(t, t1, seed=start_index + 1)
    # Pulse max (already referred to zero time)
    ek = prefix + 'expPulse'
    ep = cfg.has_key(ek)
    if ep:
        ep = cfg[ek]
    if cfg['base_expFit'] and ep:
        params.maxPulse = cfg['base_laserMax'] / 1000.
        logging.debug('Enabled exponential pulse model',
                      cfg['base_expFit'], ep, params.maxPulse)
    else:
        params.maxPulse = 0
        logging.debug('Disabled exponential pulse model', 
                      cfg['base_expFit'], ep)
        
    # Dynamic depletion
    mp = cfg[prefix + 'maxPoints']
    params.time = parameters.deplete(t[start_index:end_index], mp)
    params.temperature = parameters.deplete(signal[start_index:end_index],
                                            mp)
    params.confdb = confdb
    return params

def adjust_diffuisivity_guess_tooltip(conf, key, old, val):
    d=conf.gete(key)
    if d.get('callback_set', False)!="adjust_diffuisivity_guess_tooltip":
        return val
    from misura.client.live import registry
    sec = key.split('_')[0]
    equals = []
    from .. import legacy_options, legacy_values
    for i, name in enumerate(legacy_values):
        if name not in conf:
            return val
        if abs(val-conf[name])<0.00001:
            equals.append(legacy_options[i]) 
    if not equals:
        conf.setattr(key, 'toolTip', 'Custom diffusivity value')
    else:
        equals = ', '.join(equals)
        conf.setattr(key, 'toolTip', _('Initialized to {}').format(equals))
    registry.force_redraw([conf.getattr(key, 'kid')])
    return val
    
    
option.ConfigurationProxy.callbacks_set.add(adjust_diffuisivity_guess_tooltip)


def calc_halftime(halftime, pulse_dur, shape_halftime, shot_endtime):
    ht = halftime * 1000.
    shape_halftime_ms = shape_halftime*1000
    # If no reasonable starttime is provided, calculate it
    if ht<=pulse_dur or ht<shape_halftime_ms/10:
        logging.debug('No reasonable halftime provided. Guessing it:', ht, shape_halftime_ms)
        ht = shape_halftime_ms
    if ht>=shot_endtime:
        logging.error('calc_halftime exceeds shot duration:', ht, shot_endtime)
        ht = shot_endtime/3
    halftimeSrc = pulse_dur + ht
    return ht, halftimeSrc

def adjust_jumpPoints_endTime_expPulse(cfg, key, old, val):
    prefix = key.split('_')
    if len(prefix)>=2:
        prefix = prefix[0]+'_'
    else:
        prefix = ''
        
    if 'base_expFit' in cfg:
        expFit = cfg['base_expFit']
        laserMax = cfg['base_laserMax']
    elif 'base_expFit' in cfg.parent():
        expFit = cfg.parent()['base_expFit']
        laserMax = cfg.parent()['base_laserMax']
    else:
        return val
        
    # Use pulse duration to correct start/end
    pulse_dur = 0.1 # 20us*5
    if expFit:
        pulse_dur = laserMax * 5 # ms
    jpopt = cfg.gete(prefix+'jumpPoints')
    if not 'shape_halftime' in jpopt:
        return val
    shape_halftime = jpopt['shape_halftime']
    shape_start_time = jpopt['shape_start_time']
    shot_endtime = jpopt['shot_endtime']
    
    ht, halftimeSrc = calc_halftime(cfg['halftime'], pulse_dur, shape_halftime, shot_endtime)
    cfg[prefix + 'halftimeSrc'] = halftimeSrc
    
    opt = prefix+'expPulse'
    ep = opt in cfg
    expPulse = False
    if ep and ht/pulse_dur>100:
        if key.endswith('expPulse'):
            val = False
        cfg.setattr(opt, 'current', False)
        cfg.add_attr(opt, 'ReadOnly')
        cfg.setattr(opt, 'toolTip', 'Pulse is too short with respect to halftime.')
        logging.debug('Disabled exponential pulse: pulse is too short', pulse_dur, ht)
    elif ep:
        expPulse = cfg[opt]
        cfg.del_attr(opt, 'ReadOnly')
        cfg.setattr(opt, 'toolTip', '')
        logging.debug('Eligible for exponential pulse:', pulse_dur, ht)
        
    # Configure analysis start time using pulse_dur and halftime info
     
    if key.endswith('expPulse'):
        expPulse = val
    if key.endswith('endTime'):
        endTime = val
        if ht:
            cfg.setattr(prefix+'halftimeTimes', 'current', endTime/halftimeSrc)
    else: 
        endTime = cfg[prefix+'endTime']
        
    if ep and expPulse and expFit:
        startTime = shape_start_time*1000.
    else:
        startTime = pulse_dur + (ht / 10)
        
    if jpopt['current']==jpopt['factory_default']:
        logging.debug('Auto jumpPoints after expPulse', startTime)
        cfg.setattr(prefix+'jumpPoints', 'current', startTime)
    cfg.setattr(prefix+'jumpPoints', 'factory_default', startTime)
    
    cfg.setattr(prefix+'endTime', 'min', cfg[prefix+'jumpPoints'])
    max_endTime = ht*100 if expPulse else shot_endtime
    cfg.setattr(prefix+'endTime', 'max', max_endTime)
    
    default_endTime = cfg[prefix+'halftimeTimes']*cfg[prefix+'halftimeSrc']
    default_endTime = min(default_endTime, max_endTime)
    if not key.endswith('endTime'):
        cfg.setattr(prefix+'endTime', 'factory_default', default_endTime)
    
    endTime = min(endTime, max_endTime)
    if key.endswith('endTime'):
        val = endTime
    elif endTime==max_endTime:
        cfg.setattr(prefix+'endTime', 'current', endTime)
        
    from misura.client.live import registry
    registry.force_redraw([cfg.getattr(prefix+'jumpPoints', 'kid')])
    registry.force_redraw([cfg.getattr(prefix+'endTime', 'kid')])
    if ep:
        registry.force_redraw([cfg.getattr(prefix+'expPulse', 'kid')])
    registry.force_redraw([cfg.getattr(prefix+'halftimeTimes', 'kid')])
    return val

def guess_diffusivity(cfg, preconf, params, prefix='jg2d_', suffix='' ):
    """Reasonable guessing for diffusivity"""
    guess, name = params.__class__(confdb).get_legacy_diffusivity_guess(cfg)
    fallback(prefix + 'guessDiffusivity'+suffix,
             guess, preconf, cfg)
    
    cfg.setattr(prefix + 'guessDiffusivity'+suffix, 'toolTip', _('Initialized to {} value').format(name))
    return cfg   
    
def guess_defaults(cfg, preconf, params, t, signal, prefix='jg2d_', suffix=''):
    if not preconf:
        preconf = cfg
    cfg = guess_diffusivity(cfg, preconf, params, prefix=prefix, suffix=suffix)
    guessBiot = 0.1
    fallback(prefix + 'guessBiot', guessBiot, preconf, cfg)
    
    # Use pulse duration to correct start/end
    pulse_dur = 0.1 # 20us*5
    if cfg['base_expFit']:
        pulse_dur = cfg['base_laserMax'] * 5 # ms
        
    t1, data, Tmax, shape_halftime, shape_start_time = shapefit.shape_guess(t, 
                                                     signal, 
                                                     pulse_dur, 
                                                     cfg['base_constant'])
    
    fallback(prefix + 'guessTmax', Tmax, preconf, cfg)
    
    # Evaluate halftime and halftimeSrc
    shot_endtime = t[-1]*1000.
    ht, halftimeSrc= calc_halftime(cfg['halftime'], pulse_dur, shape_halftime, shot_endtime)
    cfg[prefix + 'halftimeSrc'] = halftimeSrc
    
    nht_opt = prefix + 'halftimeTimes'
    nht_def0 = confdb['flash_{}halfTimes'.format(prefix)]
    nht_def = cfg.parent().search_parent_key(nht_opt, default=nht_def0)
    nhtt = fallback(nht_opt, nht_def, preconf, cfg)
    
    endTime = nhtt * halftimeSrc
    fallback(prefix + 'endTime', endTime, preconf, cfg)

    # Autodisable
    opt = prefix+'expPulse'
    ep = opt in cfg
    pulse_dur = pulse_dur or 1e-6
    if ep and ht/pulse_dur>50:
        cfg[opt] = False
        cfg.add_attr(opt, 'ReadOnly')
        cfg.setattr(opt, 'toolTip', 'Pulse is too short with respect to halftime.')
        logging.debug('Disabled exponential pulse: pulse is too short', pulse_dur, ht)
    elif ep:
        cfg.del_attr(opt, 'ReadOnly')
        cfg.setattr(opt, 'toolTip', '')
        logging.debug('Eligible for exponential pulse:', pulse_dur, ht)
    
    # Configure analysis start time using pulse_dur and halftime info
    if ep and cfg[opt] and cfg['base_expFit']:
        startTime = shape_start_time*1000.
    else:
        startTime = pulse_dur + (ht / 10)
    fallback_startTime = startTime
    logging.debug('fallback_startTime', startTime)
    jumpPoints = cfg[prefix + 'jumpPoints']
    final_endTime = cfg[prefix+'endTime']
    if jumpPoints >=0 and jumpPoints < final_endTime:
        fallback_startTime = cfg[prefix + 'jumpPoints']
    fallback(prefix + 'jumpPoints', fallback_startTime, preconf, cfg, lambda v: v<0)
    if cfg[prefix + 'jumpPoints'] > final_endTime:
        cfg[prefix + 'jumpPoints'] =  fallback_startTime
       
    # Remembere key values for callback_set
    cfg.setattr(prefix+'jumpPoints', 'shape_start_time', shape_start_time)
    cfg.setattr(prefix+'jumpPoints', 'shape_halftime', shape_halftime)
    cfg.setattr(prefix+'jumpPoints', 'shot_endtime', shot_endtime)
    
    # Baseline
    fallback(prefix + 'guessBaseline', cfg['base_constant'], preconf, cfg, lambda v: v is None)
    # Baseline slope
    fallback(prefix + 'guessBaselineSlope', cfg['base_coefficient'], preconf, cfg, lambda v: v is None)
       
    calculated = {'guessBiot': guessBiot, 'guessTmax': Tmax, 'halftimeSrc': pulse_dur + ht, 
                  'endTime': nht_def0*halftimeSrc, 'guessBaseline': cfg['base_constant'],
                  'guessBaselineSlope': cfg['base_coefficient'], 'jumpPoints': startTime,
                  'halftimeTimes': nht_def0}
        
    for n in calculated.keys():
        if (prefix+n) not in cfg:
            continue
        cfg.setattr(prefix+n, 'factory_default', calculated[n])
         

option.ConfigurationProxy.callbacks_set.add(adjust_jumpPoints_endTime_expPulse)

class AbstractFlashModelPlugin(OperationWrapper, plugins.ToolsPlugin):
    _params_class = parameters.Params
    params = False
    pre_applied = False
    post_process_callback = lambda *a, **k: 1
    queue = False
    guess_diffusivity_suffix = ''
    
    
    def __init__(self, root=None, overwrite=False, silent=False, nosync=True,  output=False, notify=False):
        """Make list of fields."""
        if not output:
            output = self._output
        self.fields = [
            FieldMisuraNavigator(
                "root", descr="Select root node:", default=root),
            plugins.FieldBool(
                "overwrite", 'Overwrite previous results', default=overwrite),
            plugins.FieldBool(
                "silent", 'Hide parameters dialog', default=silent),
            plugins.FieldBool(
                "nosync", 'Asynchronous execution', default=nosync),
            plugins.FieldText(
                "output", 'Output node name', default=output),
            plugins.FieldBool(
                "notify", 'Notify after post_process', default=notify),
        ]
        self.results = []
        self.configuration_proxy = False
        self.params_pickle = False

        
    def __getstate__(self):
        result = self.__dict__.copy()
        result.pop('queue')
        return result

    @property
    def _section(self):
        return self._params_class.section

    @property
    def _output(self):
        return self._params_class.output_node

    @property
    def _handle(self):
        return self._params_class.handle

    @property
    def _name(self):
        return self._params_class.section_name

    @property
    def _prefix(self):
        return self._params_class.section + '_'

    def show_plugin_window(self, configuration_proxy):
        logging.debug('Defining the plugin config panel')
        ui = self.node_configuration_dialog(configuration_proxy, self._section, hide=True)
        section_box = ui.interface.sectionsMap[self._section]
        from .. import flashdir
        wg = QtGui.QLabel()
        wg.setPixmap(
            QtGui.QPixmap(flashdir + '/plugin/{}.png'.format(self._section)))
        section_box.config_section.lay.insertRow(0, wg)
        section_box.config_section.expand()
        section_box.config_section.expand_children()
        section_box.status_section.collapse()
        section_box.status_section.hide()
        section_box.results_section.collapse()
        section_box.results_section.hide()
        ui.setGeometry(100, 100, 600, 800)
        ok = ui.exec_()
        if not ok:
            self.params = False
            self.signal = False
            self.t = False
            self.cfg = False
            return False
        return True
    
    def get_plugin_configuration(self, node, preconf=False, silent=False):
        # Limit this to shots only
        cp = self.get_node_configuration(
            node, rule='/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+$')
        self.params = self._params_class(confdb)
        self.params.create_plugin_options(cp, preconf, aggregate=False)
        self.configuration_proxy = cp
        r = self.load_datasets(node, preconf, silent)
        if not r:
            return False
        self.create_params(node, self.cfg)        
        return True
        
            
    def create_params(self, node, cfg):
        """Create params instance starting from cfg"""
        self.params = get_params(
            cfg, self.signal.data, self.t.data, self._params_class, prefix=self._prefix)
        self.params.job = self.name+':'+node.path
        # Forget data
        if not self.signal.m_name in self.doc.data:
            self.signal.data = np.array([])
        
    
    def _guess_diffusivity(self, cfg, preconf):
        """Reasonable guessing for diffusivity"""
        guess, name = self._params_class(confdb).get_legacy_diffusivity_guess(cfg)
        fallback(self._prefix + 'guessDiffusivity',
                 guess, preconf, cfg)
        
        cfg.setattr(self._prefix + 'guessDiffusivity', 'toolTip', _('Initialized to {} value').format(name))
        return cfg    

    def load_datasets(self, node, preconf=False, silent=False):
        # FIXME: if parallel, this should return datasets unpickling locations and if baseline should run or not
        # Parallel exec should return new pickling locations to add to cache.
        # FLTD-192
        cfg = self.configuration_proxy
        signal = False
        if not cfg.has_key('base_constant'):
            logging.info('Pre-apply BaselinePlugin')
            t, raw, laser = Baseline.get_baseline_datasets(
                node, self.doc, not silent)
            if False in (t, raw, laser):
                logging.info('Failed to load baseline datasets. Aborting shot', node.path)
                return False
            cfg, t, signal_op = Baseline.run_baseline_on_proxy(
                cfg, t, raw, laser, node)
            signal = signal_op.dataset
            self.doc.add_cache(signal, signal_op.datasetname)

            t.m_name = node.path + '/corrected_t'
            self.doc.add_cache(t, node.path + '/corrected_t')
            t.m_name = node.path + '/raw_t'
            self.doc.add_cache(t, node.path + '/raw_t')
            t.m_name = node.path + '/laser_t'
            self.doc.add_cache(t, node.path + '/laser_t')

        # Reload silently from file
        if signal is False or t is False:
            outdatasets = self.doc.load_rule(node.linked.filename,
                                             '{0}/corrected$'.format(
                                                 node.path.split(':').pop(-1)),
                                             dryrun=True,
                                             overwrite=False,
                                             version=node.linked.params.version)
            cp = node.path + '/corrected'
            signal = outdatasets.get(cp, self.doc.get_cache(cp))
            t_name = node.path + '/corrected_t'
            t = outdatasets.get(t_name, self.doc.get_cache(t_name))
            
        guess_defaults(cfg, preconf, self.params, t.data, signal.data, 
                       prefix=self._prefix, suffix=self.guess_diffusivity_suffix)
        self.t = t
        self.signal = signal
        self.cfg = cfg
        return True
        

    def pre_apply(self, cmd, fields, parallel=False):
        self.pre_applied = False
        self.cmd = cmd
        self.doc = cmd.document
        self.input_fields = fields
        self.node = fields['root']
        self.outname = self.input_fields.get('output', self._output)
        self.outpath = self.node.path + '/' + self.outname
        if not hasattr(self.doc, 'plugin_process'):
            self.doc.plugin_process = {}
            
        silent = fields.get('silent', False)
        r = self.get_plugin_configuration(self.node,
                                      preconf=self.input_fields.get(
                                          'preconf', False),
                                      silent=silent)
        if r and not silent:
            r = self.show_plugin_window(self.cfg)
            if not r:
                return False
            # Read updated configuration in params
            self.params.read_configuration(self.cfg)
        if r and parallel:
            handle, self.params_pickle = tempfile.mkstemp()
            os.write(handle, dumps(self.params))
            del self.params
            os.close(handle)
        self.pre_applied = True
        return r

    def apply(self, cmd, fields, queue=False, command=False):
        r = self.pre_apply(cmd, fields, parallel=False)
        if not r:
            return False
        self.params.queue = queue or self.params.queue
        self.params.command = command or self.params.command
        if not r:
            raise plugins.ToolsPluginException('Cannot apply {} to {}'.format(self.__class__.name, self.node.path))
        if fields.get('nosync', True):
            self.async_process()
        else:
            logging.warning('AbstractModel.apply: SYNCHRONOUS EXECUTION!')
            self.process()
        logging.debug('AbstractModel.apply: done')
        return True

    def async_process(self, *args):
        """Execute process() in a separate thread"""
        p = threading.Thread(target=self.process, args=args)
        p.start()
        self.doc.plugin_process[
            self.__class__.__name__ + self.node.path] = p
        logging.debug('AbstractModel.async_process started new thread', p)

    def process(self):
        if not self.configuration_proxy:
            silent = self.input_fields.get('silent', False)
            r = self.get_plugin_configuration(self.node,
                                          preconf=self.input_fields.get(
                                              'preconf', False),
                                          silent=silent)
            if r and not silent:
                r = self.show_plugin_window(self.cfg)
                if not r:
                    return False
        if not self.configuration_proxy or not self.params:
            return False

        self.params = self.do(self.params)
        if not self.params:
            logging.error(self._name + ' plugin execution aborted')
            return False
        self.post_process()
        return True

    def post_process(self):
        # Update configuration with results
        logging.debug('post_process')
        cp = self.configuration_proxy
        if self.params is False:
            logging.debug('Skipping post_process: failed fitting', self.outpath)
            # Unload heavy objects
            self.tasks.done(self.params.job)
            del self.signal
            del self.t
            return False
        params = self.params
        signal = self.signal
        t = self.t
        cp[self._prefix + 'log'] = params['log']
        cp[self._prefix + 'std'] = float(params.error)
        logging.debug('Setting results', params, params.keys())
        for name in params.result_names + params.error_names + ['duration', 'iterations']:
            f = float(params[name])
            # Protect against nans
            if not np.isfinite(f):
                f = 0
            cp[self._prefix + name] = f

        cp[self._prefix + 'funcEval'] = float(params.progress)
        # Create model node
        outname = self.outname
        outpath = self.outpath
        if not cp.has_child(outname):
            output_proxy = params.create_output_object(cp)
            cp.add_child(outname, {'self': output_proxy})
        
        output_proxy = cp.child(outname)
        populate_output_object(cp, output_proxy, prefix=self._prefix)
        
        params.propagate(output_proxy)
        
        # Update aggregates and generate table datasets
        output_proxy.update_aggregates()
        
        # Save/cache results datasets
        op_theory = new_dataset_operation(signal, params.uncorrected,
                                          'theory',
                                          'Fitted signal', outpath + '/theory',
                                          unit='volt',
                                          opt=output_proxy.gete('theory'))
        
        ropt = output_proxy.gete('residuals')
        op_residuals = new_dataset_operation(signal, params.residuals,
                                             'residuals',
                                             'Residuals',
                                             outpath + '/residuals',
                                             unit = ropt.get('unit','volt'),
                                             opt=ropt)
        
        # Create local time datasets
        topt = option.ao({}, 'theory_t', 'Float', 0, 'Time',
                         unit='second').values()[0]
        top_time = new_dataset_operation(t, params.time,
                                        'theory_t',
                                        'Time', outpath + '/theory_t',
                                        opt=topt)
        ropt = option.ao({}, 'residuals_t', 'Float', 0, 'Time',
                         unit='second').values()[0]    
        rop_time = new_dataset_operation(t, params.time,
                                        'residuals_t',
                                        'Time', outpath + '/residuals_t',
                                        opt=ropt)
        
        # FIXME: should be a later callback!!!
        self.results = [op_theory, op_residuals, top_time, rop_time]
        self.configuration_proxy = cp
        pname = self.__class__.__name__ + self.node.path
        if pname in self.doc.plugin_process:
            self.doc.plugin_process.pop(pname)

        # Create theory dataset
        datasets = recurse_generate_datasets(
            self.configuration_proxy.root, '^{}$'.format(outname))
        
        add_datasets_to_doc(datasets, self.doc)

        silent = self.input_fields.get('silent', False)
        for op in self.results:
            if silent and not self.doc.data.has_key(op.datasetname):
                self.doc.add_cache(op.dataset, op.datasetname)
                op.dataset.data = np.array([])
                self.doc.available_data[op.datasetname] = op.dataset
            else:
                # Update the in-doc dataset
                self.ops.append(op)

        self.apply_ops()

        # Unload heavy objects
        if not params.failed:
            self.tasks.done(self.params.job)
        del self.params
        del self.signal
        del self.t
        #Non-recursive
        if self.input_fields.get('notify') or (not self.input_fields['silent']):
            self.node.insert(outpath + '/theory')
            self.node.insert(outpath + '/residuals')
            self.node.insert(outpath + '_t')
        
        return True
    
    def do_abort(self):
        logging.debug('User asked ABORT', self.params.job)
        self.params.abort = 1
        self.params.command.put(('do_abort', ))
        self.tasks.done(self.params.job)
    
            
    def do(self, params=False, queue=False, command=False):
        logging.debug('AbstractModel.do', self.params_pickle, params, queue, command)
        # Recover params from pickled tempfile
        if self.params_pickle:
            params = loads(open(self.params_pickle, 'rb').read())
            os.remove(self.params_pickle)
            self.params_pickle = False
        params.queue = queue or params.queue
        params.command = command or params.command
        logging.debug('AbstractModel.do', params.queue, params.command)
        self.params = params
        job = self.name + ':' + self.node.path
        params.job = job
        self.tasks.jobs(200, job, self.do_abort)
        # Allow the jobs call to reach the tasks widget
        sleep(0.05)
        r = self._params_class.fit_func[0](params.time,
                                           params.temperature,
                                           params, filename=params.filename)

        if params.abort:
            logging.debug('AbstractModel.do aborted')
            return False
        logging.debug('AbstractModel.do done')
        return params
