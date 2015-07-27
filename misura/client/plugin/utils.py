#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utilities for veusz-baset plugins"""
import veusz.plugins as plugins
import veusz.document as document
import numpy as np


def searchFirstOccurrence(base, typename, direction=0):
    """Search for the nearest occurrence of a widget of type `typename` starting from base. 
    The search can be restricted to upward (`direction`=-1), downward (`direction`=1) or both (`direction`=0)."""
    if isinstance(typename, str):
        typename = [typename]
    if base.typename in typename:
        return base
    # Search down in the object tree
    if direction >= 0:
        for obj in base.children:
            if obj.typename in typename:
                return obj

        for obj in base.children:
            found = searchFirstOccurrence(obj, typename, direction=1)
            if found is not None:
                return found
        # Continue upwards
        if direction == 0:
            direction = -1
    # Search up in the object tree
    # Note: exclude siblings - just look for parents
    if direction < 0:
        found = searchFirstOccurrence(base.parent, typename, direction=-1)
        if found is not None:
            return found
    # Nothing found
    return None


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


class OperationWrapper(object):

    """Helper class for operation-based objects like ToolPlugins or custom widgets"""
    name = 'OperationWrapper'
    _ops = False
    preserve = None

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
