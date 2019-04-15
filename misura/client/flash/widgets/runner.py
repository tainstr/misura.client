#!/usr/bin/python
# -*- coding: utf-8 -*-
import multiprocessing
from traceback import format_exc
import functools
from time import time, sleep

from misura.canon.logger import get_module_logging
from __builtin__ import True
logging = get_module_logging(__name__)
from misura.canon.option import match_node_path

from misura.client.widgets.active import RunMethod
from misura.canon.plugin import node

from thegram.model.parameters import execute_queue 
from ..plugin.Baseline import BaselinePlugin
from ..plugin import check_complete_sample, check_complete_segment, check_complete_test
from misura.client.conf import InterfaceDialog
from misura.client.clientconf import confdb
from misura.client import _

from PyQt4 import QtGui, QtCore

def add_enabled_flag(out, section, default=False):
    for key in ('jumpPoints', 'endTime'):
        key = section+'_'+key
        if not key.startswith(section):
            continue
        opt = out.gete(key)
        f = opt.get('flags',{})
        if f.get('enabled', None) is None:
            f['enabled']=default
            opt['flags'] = f
            out.sete(key, opt)
    return out

def review_model_setting(out, params_obj, skip=True):
    """Model dialog for recursion. Returns 0 if aborted, 
    1 if full recursion, 2 if skipping already analyzed"""
    section = params_obj.section
    logging.debug('Review model settings', out['fullpath'])
    out = add_enabled_flag(out, section)
    ui = InterfaceDialog(out)
    btn_skip = QtGui.QCheckBox(_('Skip already analyzed shots'))
    btn_skip.setTristate(False)
    btn_skip.setCheckState(2*skip)
    ui.layout().insertWidget(-2, btn_skip)
    ui.setWindowTitle(_('Review settings for recursive {} run').format(section))
    ui.interface.show_section(section, hide=True)
    sec = ui.interface.sectionsMap[section]
    sec.config_section.expand()
    sec.config_section.expand_children()
    sec.status_section.collapse()
    sec.status_section.hide()
    sec.results_section.collapse()
    sec.results_section.hide()
    ok = ui.exec_()
    if not ok:
        return False
    return 1+bool(btn_skip.checkState())

def check_already_analyzed(node, section_name):
    """Check if `node` already has one output child for model `section_name`"""
    analyzed = False
    conf = node.get_configuration()
    if not conf:
        logging.error('Cannot get configuration for node!', node.path, conf)
        return analyzed
    for child in conf.devices:
        if not child:
            continue
        if 'model' in child and child['model']==section_name:
            analyzed = True
            break
    logging.debug('check_already_analyzed', node.path, analyzed)
    return analyzed

class FlashModelNavigatorFragment(QtCore.QObject):
    """
    Recursion management
    """
    sig_queue_timer_stop = QtCore.pyqtSignal()
    sig_queue_timer_start = QtCore.pyqtSignal()
    pool = False
    results = []
    plugins = []
    pre_apply = False
    recursion_pid = 'Recursive model execution'
    recursion_progress = 0
    recursion_start_node = None
    last_model_name = None
    _last_page_edited = None
    post_recursion_callback = lambda *a: 1
    on_next_sigConfProxyModified_func = lambda *a, **k: 1
    _timer = None
    queues = {}
    commands = {}
    
    @node
    def run_baseline(self, node=False):
        """Run the baseline plugin on node"""
        p = BaselinePlugin(root=node)
        p.apply(self.navigator.cmd, {'root': node})

    @node
    def run_model_plugin(self, node=False, silent=False, nosync=True, preconf=False,
                         plugin=None, repeat=False, model_plot_options=False, callback=False):
        """Run model starting from node"""
        self.queues = {node.path: multiprocessing.Queue(1000)}
        self.commands = {node.path: multiprocessing.Queue(5)}
        conf = node.linked.conf.toPath(node.path.split(':')[-1])
        qpath = node.path
        # Target node should be shot if selected node was model
        if conf.has_key('model'):
            # Copy model node options up to the shot node
            plugin._params_class.propagate_input_parameters(
                conf.parent(), conf, force=True)
            if not preconf:
                preconf = conf
            # Replace with the parent node
            node = node.parent
            silent = True
            repeat = True
        p = plugin(root=node, silent=silent)
        r = p.apply(self.navigator.cmd, {'root': node, 'silent': silent,
                                     'nosync': nosync, 'preconf': preconf or conf,
                                     'notify': True},
                                    queue=self.queues[qpath], command=self.commands[qpath])
        if not r:
            logging.info('Aborting model exec', plugin.name)
            self.cleanup()
            return False
        # Starts the timer
        self.execute_queue()
        self.sig_queue_timer_stop.connect(self.cleanup)
        self.sig_queue_timer_start.connect(self.pause_before_model_execution)
        self.timer_stopped_callback = callback
        self.sig_queue_timer_stop.connect(self.call_timer_stopped_callback)
        #if callback:
            # LEADS TO INFINITE LOOP:
            #self.sig_queue_timer_stop.connect(callback)
            # NOT SUPPORTED:
            #self.sig_queue_timer_stop.connect(functools.partial(self.sig_queue_timer_stop.disconnect, callback))
        
        conf.root.flash.measure['fitting'] = p._name
        
        if (not silent) or repeat:
            mpo = model_plot_options or {}
            self.on_next_sigConfProxyModified_func = functools.partial(self.plot_after_model, node.path, p.outname, **mpo)
            self.doc.sigConfProxyModified.connect(self.on_next_sigConfProxyModified)
        if nosync:
            # Pause again
            self.start_queue_timer()
            QtCore.QTimer.singleShot(100, functools.partial(self.navigator.pause, True))
        else:
            logging.debug('Finished run_model_plugin')
            self.stop_queue_timer()
        return True
    
    def call_timer_stopped_callback(self):
        if self.timer_stopped_callback:
            logging.debug('timer_stopped_callback')
            self.timer_stopped_callback()
        self.sig_queue_timer_stop.disconnect(self.call_timer_stopped_callback)
            
    _queue_timer = False
    def start_queue_timer(self):
        if not self._queue_timer:
            self._queue_timer = QtCore.QTimer()
            # Real execution starts when pre_apply ends
            self._queue_timer.timeout.connect(self.execute_queue, QtCore.Qt.QueuedConnection)
        self._queue_timer.start(1000)
        logging.debug('start_queue_timer', self._queue_timer.interval())
    
    def stop_queue_timer(self):
        logging.debug('stop_queue_timer')
        if self._queue_timer:
            self._queue_timer.stop()
        self.queues = {}
        self.commands = {}
        self.sig_queue_timer_stop.emit()
        
    def pause_before_model_execution(self):
        self.navigator.pause(1)
        self.doc.suspendUpdates()
         
               
    def plot_after_model(self, node_path, outname, **kw):
        node = self.doc.model.tree.traverse_path(node_path+'/'+outname)
        logging.debug('plot_after_model', outname, node_path, outname, node)
        if not node:
            return False
        # Force overwriting of the plot
        if 'force' not in kw:
            kw['force'] = True
        self.model_plot(node, **kw)
        
            
    def on_next_sigConfProxyModified(self):
        """Execute on_next_sigConfProxyModified and disconnect"""
        logging.debug('on_next_sigConfProxyModified')
        self.doc.sigConfProxyModified.disconnect(self.on_next_sigConfProxyModified)
        self.on_next_sigConfProxyModified_func()
        

    def prepare_recursive_plugin(self, node, conf, nosync=True, plugin=None, skip=False):
        """Prepare plugins structure for parallel execution"""
        p = False
        for key, child in node.children.iteritems():
            # Continue the iteration at deeper levels
            if not match_node_path(child, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+$'):
                self.prepare_recursive_plugin(child, conf, nosync, plugin=plugin, skip=skip)
                continue
            # Skip if already analyzed
            if skip and check_already_analyzed(child, plugin._params_class.section_name):
                logging.debug('Skip already analyzed shot:', child.path)
                continue
            if not nosync:
                self.run_model_plugin(
                    child, silent=True, nosync=False, preconf=conf, plugin=plugin)
                continue

            p = plugin()
            fields = {
                'root': child, 'silent': True, 'nosync': False, 'preconf': conf}
            
            self.plugins[child.path] = (p, child, (self.navigator.cmd, fields, True))
            logging.debug('_recursive_plugin done')
        
        if p:
            conf.root.flash.measure['fitting'] = p._name
            
    _manager = False
    @property
    def manager(self):
        if not self._manager:
            self._manager = multiprocessing.Manager()
        return self._manager
    
    def recursive_plugin(self, node, conf, nosync=True, plugin=None, skip=False):
        """Run jg2d model on any applicable node under `node`"""
        self.post_recursion_callback = lambda *a, **k: 1
        self.plugins = {}
        self.results = {}
        self.pool = multiprocessing.Pool(confdb['maxcpu'])
        # Prepare self.plugins mapping
        self.prepare_recursive_plugin(node, conf, nosync, plugin=plugin, skip=skip)
        self.queues = {}
        # Pre-apply plugins in a separate thread, so they can load their data
        def func():
            rem = []
            for i, (p, node, args) in enumerate(self.plugins.values()):
                logging.debug('PRE-APPLY', node.path)
                if not p.pre_apply(*args):
                    rem.append(node.path)
                if not self.pre_apply:
                    # Aborted
                    return False
                self.pre_apply.job(i, node.path)
            # Remove failed plugins
            for npath in rem[::-1]:
                self.plugins.pop(npath)
        # Threading has the sole purpose of not blocking user interface
        # And displaying a progress bar
        self.pre_apply = RunMethod(func)
        self.pre_apply.step = len(self.plugins)
        self.pre_apply.pid = 'Pre apply'
        
        # Periodically poll the the thread and start real execution once
        # finished
        if nosync:
            # Async pre-apply
            self.pre_apply.do()
            self.recursion_pid = 'Recursive '+plugin._params_class.section_name
            self.recursion_progress = 0
            self.navigator.tasks.jobs(len(self.plugins) * 2,
                                      self.recursion_pid,
                                      abort=self.recursion_abort)
            self._timer = QtCore.QTimer()
            self._timer.setInterval(1000)
            self._timer.timeout.connect(self._execute_recursion)
            self._timer.start()
            QtCore.QTimer.singleShot(100, self.pause_before_model_execution)
        else:
            self.pause_before_model_execution()
            # Sync pre-apply
            self.pre_apply.run()
            self._execute_recursion(nosync)
            self.post_process_plugins()
        
                        
    def execute_queue(self):
        logging.debug('execute_queue', self.queues.keys())
        if not self.queues and not self.plugins and not self.results:
            logging.debug('Finished queues, plugins and results.')
            self.stop_queue_timer()
            return 0
        i = 0
        for npath, q in self.queues.items():
            j, names, results = execute_queue(self.navigator.tasks, q, npath)
            i += j
            # Remove queue
            if 'done' in names or 'failed' in names:
                self.queues.pop(npath)
                self.commands.pop(npath)
        return i
    

    def _execute_recursion(self, nosync=False):
        if len(self.results)<len(self.plugins):
            self.execute_queue()
            # Define results
            logging.debug('Mapping jobs to process pool...')
            for npath, (p, node, pre_apply) in self.plugins.items():
                if not p.pre_applied:
                    print 'Skip non pre-applied', npath
                    continue
                if npath in self.results:
                    continue
                self.queues[npath] = self.manager.Queue(100)
                self.commands[npath] = self.manager.Queue(10)
                func = p.__class__._params_class.fit_params_func[0]
                job = p.__class__.name + ':' + npath
                self.navigator.tasks.jobs(1, job, functools.partial(self.single_shot_abort, npath))
                logging.debug('MAP', func, p.params_pickle, node.path)
                res = self.pool.apply_async(func, (p.params_pickle, self.queues[npath], self.commands[npath]))
                self.results[npath] = (res, node.path)
                self.recursion_progress += 1
                self.navigator.tasks.job(self.recursion_progress, 
                                         self.recursion_pid)
        else:
            # Wait for results and process them
            logging.debug('post_process_plugins',len(self.results),len(self.plugins))
            self.post_process_plugins()

    def recursion_abort(self):
        logging.error('Plugin recursion aborted!')
        self.post_process_plugins()
        # Close all pending tasks
        for npath, (p, node, pre_apply) in self.plugins.items():
            job = p.__class__.name + ':' + npath
            self.navigator.tasks.done(job)
            
        # Send abort commands
        for npath, cmd in self.commands.items():
            logging.debug('Aborting shot:', npath)
            cmd.put(('do_abort',))
        self.cleanup()
        
    def single_shot_abort(self, npath):
        logging.debug('single_shot_abort', npath)
        self.commands[npath].put(('do_abort', ))

    def post_process_plugins(self):
        # Scan until one result is ready
        self.execute_queue()
        for i, (res, npath) in enumerate(self.results.values()):
            failed = False
            try:
                params = res.get(timeout=0.01)
            except multiprocessing.TimeoutError:
                return False
            except:
                logging.error('post_process_plugins', len(self.results),
                              i, npath, res, format_exc())
                failed = True
            self.results.pop(npath)
            if npath in self.queues:
                self.queues.pop(npath)
            if npath in self.commands:
                self.commands.pop(npath)
            p = self.plugins.pop(npath)
            self.recursion_progress += 1
            if failed:
                self.navigator.tasks.job(
                    self.recursion_progress, 
                    self.recursion_pid, 'failed: '+npath)
                continue
            p[0].params = params
            p[0].post_process()
            self.navigator.tasks.job(
                self.recursion_progress, self.recursion_pid, 'done: '+npath)
            # Stop as the first result was found
            return False
        self.navigator.tasks.done(self.recursion_pid)
        self.post_recursion_callback()
        self.cleanup()
        return True
    
    def cleanup(self):
        logging.debug('CLEANUP', self.recursion_start_node)
        # If no result was found
        self.plugins = {}
        self.results = {}
        self.queues = {}
        self.commands = {}
        if self._timer:
            self._timer.stop()
            self._timer = None
            
        self.pre_apply = False
        
        self.recursion_start_node = None
        self.navigator.pause(False)
        if self.doc.suspendupdates:
            self.navigator.doc.enableUpdates()
        # theoretically correct, but causes FLTD-604
        #self.post_recursion_callback = lambda *a, **k: 1
        
        self.doc.sigConfProxyModified.emit()
        
        if self.pool:
            sleep(3)
            self.pool.terminate()
            self.pool.join()
    @node
    def run_recursive_plugin_sample(self, node, plugin=None, callback=False, read_conf=False):
        # Ask for d, L, OI, II, OV, IV
        conf = node.get_configuration()
        p = plugin._params_class(confdb)
        p.add_sample_options(conf, overwrite=False)
        p.add_diameters(conf, overwrite=False)
        p.create_plugin_options(conf, conf, aggregate=True)
        p.add_optimization_names(conf, overwrite=False)
        
        # If a source was defined, copy any available setting
        if read_conf:
            red = p.read_configuration(read_conf)
            red = set(red)-set(p.result_names+p.introspection_names)
            map(lambda k: conf.setattr(p.prefix+k, 'current', read_conf[p.prefix+k]), red)
            logging.debug('Copied', red)
        
        # Review the settings
        complete = check_complete_sample(conf, p.section_name)
        r = review_model_setting(conf, p, skip=not complete)
        if not r:
            return False
        # Run the model runner instead...
        self.recursion_start_node = node
        self.recursive_plugin(node, conf, nosync=True, plugin=plugin, skip=r-1)
        if callback:
            self.post_recursion_callback = callback
        else:
            self.post_recursion_callback = functools.partial(self.sample_plot, node.path, force=True)
        return True

    @node
    def run_recursive_plugin_segment(self, node, plugin=None, callback=False, read_conf=False):
        # Ask for OI, II, OV, IV
        conf = node.get_configuration()
        p = plugin._params_class(confdb)
        p.confdb = confdb
        p.add_sample_options(conf, overwrite=False)
        p.add_diameters(conf, overwrite=False)
        p.create_plugin_options(conf, conf, aggregate=True)
        p.add_optimization_names(conf, overwrite=False)
        
        # If a source was defined, copy any available setting
        if read_conf:
            red = p.read_configuration(read_conf)
            red = set(red)-set(p.result_names+p.introspection_names)
            map(lambda k: conf.setattr(p.prefix+k, 'current', read_conf[p.prefix+k]), red)
            logging.debug('Copied', red)
                  
        if '/sample' in node.path:
            sample = node
            while not sample.name().startswith('sample'):
                sample = sample.parent
                if sample == sample.root:
                    sample = False
                    break
            if sample:
                logging.debug('FOUND SAMPLE', sample.path)
                sample = sample.get_configuration()

                conf[p.prefix+'diameter'] = sample['diameter']
                conf[p.prefix+'thickness'] = sample['thickness']
            # It's a segment recursion:
            complete = check_complete_segment(conf, p.section_name)
        else:
            # It's a full-test recursion:
            complete = check_complete_test(conf, p.section_name)
        
        # Review the settings
        r = review_model_setting(conf, p, skip=not complete)
        if not r:
            return False
        self.recursion_start_node = node
        self.recursive_plugin(node, conf, nosync=True, plugin=plugin, skip=r-1)
        if callback:
            self.post_recursion_callback = callback
        else:
            self.post_recursion_callback = functools.partial(self.segment_plot, node.path, force=True)
        return True
        
    @node
    def run_recursive_plugin_file(self, node, plugin=None, callback=False, read_conf=False):
        if not callback:
            callback = functools.partial(self.summary_plot, node.path, force=True)
        return self.run_recursive_plugin_segment(node, plugin=plugin, callback=callback, read_conf=read_conf)
        
        

