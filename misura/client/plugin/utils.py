#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utilities for veusz-baset plugins"""
import re
import numpy as np


import veusz.plugins as plugins
import veusz.document as document

from .. import _

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from misura.client.iutils import searchFirstOccurrence, iter_widgets
from misura.canon.csutil import smooth, smooth_discard

def convert_datapoint_units(convert_func, dsname, doc):
    """Convert all DataPoint widgets in `doc` using dataset `dsname`
    as the x or y of the curve they are attached to."""
    for wg in iter_widgets(doc.basewidget, 'datapoint', 1):
        if not wg:
            continue
        curve = wg.parent

        if not curve:
            continue

        print wg.settings.xPos, wg.settings.yPos
        if curve.settings.yData == dsname:
            wg.settings.yPos = convert_func(wg.settings.yPos[0])
            wg.actionUp()
        elif curve.settings.xData == dsname:
            wg.settings.xPos = convert_func(wg.settings.xPos[0])
            wg.actionUp()


def rectify(xData):
    """Make monotonic `xData` by inverting all negative derivative points.
    Returns rect array and derivatives array.
    Eg: [1,2,1,3] will result [1,2,3,5],[1,-1,2]"""
    # Make xData monotonic
    x = xData.copy()
    # Absolute value of point derivatives
    xd = np.diff(x)
    # Avoid plateau
    p = np.where(xd==0)[0]
    xd[p] = 1e-14
    
    # Rectification entity estimation
    xe = np.sign(np.diff(xd))
    err = 1. * (abs(xe).sum() - xe.sum()) / len(xe)

    # Cumulative sum in order to rebuild a monotonic x
    xs = np.cumsum(abs(xd))
    # Add initial value and cumulative sum
    x[1:] = x[0] + xs
    return x, xd, err


def derive(v, method, order=1):
    """Derive one time an array, always returning an array of the same length"""
    if method == 'Middle':
        return np.gradient(v, order)
    d = np.diff(v, order)
    if method == 'Right':
        app = np.array([d[-1]] * order)
        d = np.concatenate((d, app))
        return d
    app = np.array([d[0]] * order)
    d = np.concatenate((app, d))
    return d


def xyderive(x, y, order, method):
    """Compute order-th derivative of `y` with respect to `x`"""
    x = derive(x, method)
    for i in range(order):
        y = derive(y, method)
        y = y / x
    return y

class CachedResultFragment(object):
    """Extension fragment for caching plugin results"""
    cached_dataset_fields = []
    cached_result = None    
    cached_datasets = None #{}
    cached_fields = None #{}
    
    def is_cache_dirty(self, fields, helper):
        # Collect cached datasets and cached fields
        c = {}
        fc = {}
        for field, value in fields.items():
            if field not in self.cached_dataset_fields:
                fc[field] = value
                continue 
            d = np.array(helper.getDataset(value).data)
            c[field] = d
            
        # Initialize the cache
        if not self.cached_datasets:
            self.cached_datasets = c
            self.cached_fields = fc
            return True
        
        # Detect changes in other non-dataset fields
        for field, value in fc.items():
            if value!=fields[field]:
                return True
            
        # Expensive elementwise comparison
        dirty = sum([ np.all(c[i]==self.cached_datasets[i]) for i in self.cached_dataset_fields])
        dirty = dirty < len(self.cached_dataset_fields)
        # Store updated cache
        self.cached_datasets = c
        self.cached_fields = fc
        return dirty



class OperationWrapper(plugins.OperationWrapper):

    """Helper class for operation-based objects like ToolPlugins or custom widgets"""
    name = 'OperationWrapper'
    _ops = False
    preserve = None

    @property
    def registry(self):
        from .. import live
        return live.registry

    @property
    def tasks(self):
        r = getattr(self.registry, 'tasks', False)
        return r

    def validate_datasets(self, dss, up=True):
        """Check if dataset `ds` has the m_update flag."""
        n = 0
        for ds in dss:
            if not hasattr(ds, 'm_update'):
                continue
            if ds.m_update == up:
                continue
            ds.m_update = up
            n += 1
        return n

    def _(self, *a, **k):
        return _(*a, **k)

    def get_node_configuration(self, node, rule=False):
        p = node.path
        if rule:
            regex = re.compile(rule.replace('\n', '|'))
            if not regex.search(p):
                raise plugins.ToolsPluginException(
                    self._('The target does not conform to rule {}:\n {}').format(rule, p))
        if not node.linked:
            raise plugins.ToolsPluginException(
                self._('The selected node does not seem to have an associated configuration') + p)

        return node.get_configuration()

    def node_configuration_dialog(self, configuration_proxy, section='Main', hide=False):
        ui = plugins.FieldConfigurationProxy.conf_module.InterfaceDialog(
            configuration_proxy)
        ui.setWindowTitle(
            self._('Review settings for ') + configuration_proxy['fullpath'])
        ui.interface.show_section(section, hide=hide)
        return ui

    def show_node_configuration(self, configuration_proxy, section='Main'):
        ui = self.node_configuration_dialog(configuration_proxy, section)
        r = ui.exec_()
        if not r:
            logging.info('Plugin execution aborted', r)
            return False
        return True

    def set_new_dataset(self, original_dataset, data, name, label, path, unit='volt', opt=False, dryrun=False):
        """Create a new dataset by copying `original_dataset` and overwriting with `data`"""
        from ..filedata.generate_datasets import new_dataset_operation
        op = new_dataset_operation(
            original_dataset, data, name, label, path, unit=unit, opt=opt)
        if not dryrun:
            self.ops.append(op)
        return op
    
from misura.client.filedata.dataset import AbstractMisuraDataset
from veusz import dialogs
class MisuraPluginDataset1D(plugins.Dataset1D, AbstractMisuraDataset):
    def __init__(self, *a, **k):
        plugins.Dataset1D.__init__(self, *a, **k)
        AbstractMisuraDataset.__init__(self)
        
    def _makeVeuszDataset(self, manager):
        ds = plugins.Dataset1D._makeVeuszDataset(self, manager)
        # define a new derived class on the fly
        derived_class = type('Misura'+ds.__class__.__name__, (ds.__class__, AbstractMisuraDataset), {})
        dialogs.recreate_register[derived_class] = dialogs._lazy_recreate_plugin
        #FIXME: will not work with few dataset classes
        ds1 = derived_class(manager, self)
        ds1.attr = self.attr
        return ds1
        
        

