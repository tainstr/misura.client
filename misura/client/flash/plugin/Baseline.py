#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run a model in a veusz plugin"""
from copy import copy

import numpy as np

import veusz.plugins as plugins
from veusz import document
from misura.client.plugin import OperationWrapper
from misura.client.filedata.generate_datasets import new_dataset_operation
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from ..model.baseline import _run_baseline_on_proxy


def run_baseline_on_proxy(configuration_proxy, t, raw, laser, node):
    t1, corrected_signal, laser_fit, raw1, laser1 = _run_baseline_on_proxy(configuration_proxy, t.data, raw.data, laser.data)
    t.data = t1
    corrected_op = new_dataset_operation(raw, corrected_signal, 'corrected', 'Corrected signal', 
                                            node.path+'/corrected', 
                                            opt=configuration_proxy.gete('corrected'))
    
    laser_fit_op = False
    if laser_fit is not False:
        if not 'laserFit' in configuration_proxy:
            configuration_proxy.add_option('laserFit','Float',name='Laser fitting',
                                       unit='volt', attr=['History', 'Event', 'Runtime', 'Hidden'])
        laser_fit_op = new_dataset_operation(raw, laser_fit, 'laserFit', 'Laser fit', 
                                            node.path+'/laserFit', 
                                            opt=configuration_proxy.gete('laserFit'))
    
    return configuration_proxy, t, corrected_op, laser_fit_op 

def get_baseline_datasets(node, doc, loads):
    path = node.path.split(':').pop(-1)
    outdatasets = doc.load_rule(node.linked.filename, '{0}/raw$\n{0}/laser$'.format(path), 
                                     overwrite=True, 
                                     dryrun=not loads,
                                     version=node.linked.params.version)
    
    raw = outdatasets.get(node.path + '/raw')
    laser = outdatasets.get(node.path + '/laser')
    #FIXME: it appears local dataset are directly injected into the document...
    t = outdatasets.get(node.path + '/raw_t', doc.get_cache(node.path + '/raw_t'))
    return t, raw, laser


class BaselinePlugin(OperationWrapper, plugins.ToolsPlugin):

    """Run Flash baseline correction."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Flash', 'Baseline correction')
    # unique name for plugin
    name = 'Baseline'
    # name to appear on status tool bar
    description_short = 'Run Baseline correction'
    # text to appear in dialog box
    description_full = 'Run Baseline correction'
    
    def __init__(self, root=None, overwrite=False, loads=True):
        """Make list of fields."""
        self.fields = [
            plugins.FieldMisuraNavigator(
                "root", descr="Select shot node:", default=root),
            plugins.FieldBool(
                "overwrite", 'Overwrite previous results', default=overwrite),
            plugins.FieldBool(
                "loads", 'Keep loaded datasets', default=loads),
        ]
     
    def overwrite_if_exists(self, name, t):
        node = self.input_fields['root']
        loads = self.input_fields.get('loads', True)
        if self.doc.data.has_key(node.path+name):
            self.ops.append(document.OperationDatasetSetVal(node.path+name, 'data', slice(None,None), t.data))
        elif not loads:
            self.doc.add_cache(t, node.path + name) 
            
    def create_dataset_and_time(self, name, op, t): 
        """Overwrite/create/cache corrected/laserFit ds and their time"""
        nn = self.node.path+name
        if nn in self.doc.data:
            self.ops.append(document.OperationDatasetSetVal(nn, 'data', 
                                                            slice(None,None), 
                                                            op.dataset.data))
        elif self.loads:
            # Create a new dataset from "raw"dataset
            self.ops.append(op)
        else:
            op.dataset.data = np.array([])
            self.doc.available_data[op.datasetname] = op.dataset
            
        # Simply copy time ds
        tn = self.node.path+name+'_t'
        if tn in self.doc.data:
            self.ops.append(document.OperationDatasetSetVal(tn, 'data', slice(None,None), t.data))
        elif self.loads:
            self.ops.append(
                            document.OperationDatasetSet(tn, copy(t)))
        else:
            ds_t = copy(t)
            ds_t.m_name = op.datasetname+'_t'
            self.doc.add_cache(ds_t, op.datasetname+'_t')      
          
    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.doc = cmd.document
        self.node = fields['root']
        self.input_fields = fields
        configuration_proxy = self.get_node_configuration(self.node, rule='/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+$')
        self.configuration_proxy = configuration_proxy
        
        self.loads = fields.get('loads', True)
        t, raw, laser = get_baseline_datasets(self.node, self.doc, self.loads)
        configuration_proxy, t, corrected_op, laser_fit_op = run_baseline_on_proxy(configuration_proxy, t, raw, laser, self.node)
    
        
        # File-system cache for results
        if not self.loads:
            self.doc.add_cache(raw, self.node.path + '/raw')
            self.doc.add_cache(laser, self.node.path + '/laser')
            self.doc.add_cache(corrected_op.dataset, corrected_op.datasetname)
            if laser_fit_op:
                self.doc.add_cache(laser_fit_op.dataset, laser_fit_op.datasetname)
            
        self.overwrite_if_exists('/raw_t', t)
        self.overwrite_if_exists('/laser_t', t)
        
        self.create_dataset_and_time('/corrected', corrected_op, t)
        
        if laser_fit_op:
            self.overwrite_if_exists('/laserFit_t', t)
            self.create_dataset_and_time('/laserFit', laser_fit_op, t)
        
        self.apply_ops()
        
        
        return True

plugins.toolspluginregistry.append(BaselinePlugin)

