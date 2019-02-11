#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Operations between x,y, curves"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import numpy as np
from scipy import interpolate
import numexpr
import utils


class CurveOperationPlugin(plugins.DatasetPlugin):

    """Dataset plugin to perform operations between couples of x,y datasets."""
    # tuple of strings to build position on menu
    menu = ('Compute', 'Curve Operation')
    # internal name for reusing plugin later
    name = 'CurveOperation'
    # string which appears in status bar
    description_short = 'Perform operations between x,y, curves.'

    # string goes in dialog box
    description_full = ('Perform operations between (X,Y) curves.'
                        'Use A and B to refer to curves. Supports numexpr expressions.'
                        'Output curve will have the same number of points as A.')

    def __init__(self, ax='', ay='', bx='', by='', relative=False, smooth=True, tolerance=10., operation='A-B', ds_out=''):
        """Define input fields for plugin."""
        self.cache = []
        self.fields = [
            plugins.FieldDataset('ay', 'Target A: Y dataset', default=ay),
            plugins.FieldDataset('ax', 'Target A: X dataset', default=ax),
            plugins.FieldDataset('by', 'Reference B: Y dataset', default=by),
            plugins.FieldDataset('bx', 'Reference B: X dataset', default=bx),
            # TODO: might support unlimited number of curves, thanks to numexpr
            plugins.FieldText(
                'operation', 'Operation to perform. ', default=operation),
            plugins.FieldBool(
                "relative", descr="Coincident start", default=relative),
            plugins.FieldBool(
                "smooth", descr="Smooth x data", default=smooth),
            plugins.FieldFloat(
                "tolerance", descr="X rectification tolerance", default=tolerance),
            plugins.FieldDataset(
                'ds_out', 'Output dataset name', default=ds_out)
        ]
        self.error = 0

    def getDatasets(self, fields):
        """Returns single output dataset (self.ds_out).
        This method should return a list of Dataset objects, which can include
        Dataset1D, Dataset2D and DatasetText
        """
        # raise DatasetPluginException if there are errors
        if fields['ax'] == fields['ay']:
            raise plugins.DatasetPluginException(
                'Curve A (X,Y) values must differ')
        if fields['bx'] == fields['by']:
            raise plugins.DatasetPluginException(
                'Curve B (X,Y) values must differ')
        if fields['ds_out'] in (fields['ax'], fields['bx'], fields['by'], '',):
            raise plugins.DatasetPluginException(
                'Input and output datasets cannot be the same.')
        # make a new dataset with name in fields['ds_out']
        self.ds_out = plugins.Dataset1D(fields['ds_out'])
        self.error = 0
        # return list of datasets
        return [self.ds_out]

    def updateDatasets(self, fields, helper):
        ay = np.array(helper.getDataset(fields['ay']).data)
        ax = np.array(helper.getDataset(fields['ax']).data)
        by = np.array(helper.getDataset(fields['by']).data)
        bx = np.array(helper.getDataset(fields['bx']).data)
        c = [ax,ay,bx,by]
        if not self.cache:
            self.cache = c
            dirty = True
        else:
            dirty = sum([ np.all(c[i]==self.cache[i]) for i in xrange(4)])<4
            if not dirty:
                out, error = self.cache[-2:]
        if dirty:
            out, error = curve_operation(ax, ay, bx, by, fields['relative'], fields['smooth'], fields['tolerance'], fields['operation'])
            self.cache += [out,error]
        self.error = error
        self.ds_out.update(data=out)
        return out


def filter_derivatives(x, width=1, *y):
    """Returns filtering mask and filtered arrays"""
    x1= np.diff(x)
    # Generate inhomogeneity mask
    m = np.ones(len(x)).astype(np.bool)
    for i, d in enumerate(x1[width:-width]):
        i+=width
        s = np.sign(x1[i-width:i+1+width])
        main = np.round(s.mean())
        if s[width]!=main:
            m[i+1] = False
    y = list(y)
    for i, g in enumerate(y):
        y[i] = g[m]
    out = [ m, x[m] ] + y
    return out 

def curve_operation(ax, ay, bx, by, relative=True, smooth=True, tolerance=10., operation='A-B'):
    """Actually do the CurveOperationPlugin calculation."""
    op = operation.lower()

    N = len(ax)
    if len(ay) != N:
        raise plugins.DatasetPluginException(
            'Curve A X,Y datasets must have same length')

    Nb = len(bx)
    if len(by) != Nb:
        raise plugins.DatasetPluginException(
            'Curve B X,Y datasets must have same length')

    # Relativize
    if relative:
        d = by[0] - ay[0]
        by -= d
        logging.debug('relative correction', d)

    # If the two curves share the same X dataset, directly operate
    if bx is ax:
        out = numexpr.evaluate(op, local_dict={'a': ay, 'b': by})
        return out, 0

    # Smooth x data
    if smooth:
        ax = utils.smooth(ax)
        bx = utils.smooth(bx)
        

    m, rbx, rby = filter_derivatives(bx, 1, by)
    m, rax, ray = filter_derivatives(ax, 1, ay)
    if tolerance > 0:
        rax, dax, erra = utils.rectify(rax)
        rbx, dbx, errb = utils.rectify(rbx)
        logging.debug('rectification errors', erra, errb)
        if max(erra, errb) > tolerance:
            logging.error('Rectification exceeds tolerance', erra, errb, tolerance)
            raise plugins.DatasetPluginException(
                'X Datasets are not comparable in the required tolerance.')

    N = len(rbx)
    margin = 5 + int(N / 10)
    step = 5 + int((N - 2 * margin) / 100)
    logging.debug( 'interpolating', len(rbx), len(rby), margin, step)
    
    knots = rbx[margin:-margin:step]
    #knots = [5, 10, 15]
    bsp = interpolate.LSQUnivariateSpline(rbx, rby, knots)
    #bsp = interpolate.UnivariateSpline(rbx, rby)
    #errror = bsp.get_residuals()
    error = 0
    
    # Evaluate B(y) spline with A(x) array
    b = bsp(ax)
    # Perform the operation using numexpr
    out = numexpr.evaluate(op, local_dict={'a': ay, 'b': b})
    return out, error
    

# add plugin classes to this list to get used
plugins.datasetpluginregistry.append(CurveOperationPlugin)
