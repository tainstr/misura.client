#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utilities for veusz-baset plugins"""
import re
import numpy as np


import veusz.plugins as plugins
import veusz.document as document

from .. import _
from misura.canon.logger import Log as logging

from misura.client.iutils import searchFirstOccurrence, iter_widgets


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
    # Rectification entity estimation
    xe = np.sign(np.diff(xd))
    err = 1. * (abs(xe).sum() - xe.sum()) / len(xe)

    # Cumulative sum in order to rebuild a monotonic x
    xs = np.cumsum(abs(xd))
    # Add initial value and cumulative sum
    x[1:] = x[0] + xs
    return x, xd, err


def smooth(x, window=10, method='hanning'):
    """method='flat', 'hanning', 'hamming', 'bartlett', 'blackman', 'kaiser'"""
    s = np.r_[2 * x[0] - x[window - 1::-1], x, 2 * x[-1] - x[-1:-window:-1]]
    # print(len(s))
    if method == 'flat':  # moving average
        w = np.ones(window, 'd')
    else:
        w = eval('np.' + method + '(window)')
    y = np.convolve(w / w.sum(), s, mode='same')
    y = y[window:-window + 1]
    return y


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


class OperationWrapper(object):

    """Helper class for operation-based objects like ToolPlugins or custom widgets"""
    name = 'OperationWrapper'
    _ops = False
    preserve = None
    translate = [_]
    plugins_module = plugins
    document_module = document

    @property
    def registry(self):
        from .. import live
        return live.registry

    @property
    def tasks(self):
        r = getattr(self.registry, 'tasks', False)
        return r

    @property
    def ops(self):
        if not self._ops:
            self._ops = []
        return self._ops

    @ops.setter
    def ops(self, val):
        self._ops = val

    def apply_ops(self, descr=False):
        if not descr:
            if getattr(self, 'name', False):
                descr = self.name
            else:
                descr = self.typename
        if len(self.ops) > 0:
            self.doc.applyOperation(
                document.OperationMultiple(self.ops, descr=descr))
        self.ops = []

    def toset(self, out, name, val):
        """Set `name` to `val` on `out` widget"""
        name = name.split('/')
        old = out.settings.getFromPath(name).get()
        if old != val:
            #			print 'preparing toset',name,old,val
            self.ops.append(document.OperationSettingSet(
                out.settings.getFromPath(name), val))
            return False
        return True

    def cpset(self, ref, out, name):
        """Copy setting `name` from `ref` to `out`"""
        val = ref.settings.getFromPath(name.split('/')).get()
        return self.toset(out, name, val)

    def eqset(self, ref, name):
        """Set DataPoint setting `name` equal to the same setting value on `ref` widget."""
        return self.cpset(ref, self, name)

    def dict_toset(self, out, props, preserve=None):
        if preserve is None:
            preserve = self.preserve
        pd = {}
        if preserve:
            pd = getattr(out, 'm_auto', {})
# 		print 'found preserve dict',pd
        for k, v in pd.iteritems():
            if not props.has_key(k):
                continue
            cur = out.settings.getFromPath(k.split('/')).get()
            # It took a different value than the auto-arranged one
            if cur != v:
                # 				print 'dict_toset preserving',k,cur,v
                # Remove from auto assign
                props.pop(k)
        for name, value in props.iteritems():
            self.toset(out, name, value)
        # Update the m_auto attribute
        if len(pd) > 0:
            out.m_auto.update(props)
        # Create it if was missing
        elif preserve:
            out.m_auto = props
        return True

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
                raise self.plugins_module.ToolsPluginException(
                    self._('The target does not conform to rule {}:\n {}').format(rule, p))
        if not node.linked:
            raise self.plugins_module.ToolsPluginException(
                self._('The selected node does not seem to have an associated configuration') + p)

        return node.get_configuration()

    def node_configuration_dialog(self, configuration_proxy, section='Main'):
        ui = self.plugins_module.FieldConfigurationProxy.conf_module.InterfaceDialog(
            configuration_proxy)
        ui.setWindowTitle(
            self._('Review settings for ') + configuration_proxy['fullpath'])
        ui.interface.show_section(section)
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
