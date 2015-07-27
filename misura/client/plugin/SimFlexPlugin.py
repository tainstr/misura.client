#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
from misura.canon.logger import Log as logging
import veusz.plugins as plugins
import numpy
import scipy
import veusz.document as document
import numpy as np
from scipy import interpolate
from scipy.optimize import fmin


class SimFlex(object):

    """Simulation processing."""

    def __init__(self, layers, L0, minT, maxT, N=1000):
        """`layers`: a list containing layers description dictionaries, 
                        ordered from the uppermost to the bottom layer
                `L0`: initial length of the composite
                `minT`: simulation starting temperature
                `maxT`: simulation ending temperature
                `N`: number of points in the simulated curve
        """
        self.layers = layers
        self.L0 = L0
        self.minT = minT
        self.maxT = maxT
        self.N = N
        step = int((maxT - minT) / N) + 1
        self.vT = np.arange(minT, maxT, step)
        """Temperatures array"""
        # Middle position:
        hs = [mat['h'] for mat in layers]
        hm = np.sum(hs) / len(hs)  # mean position

        # layer positions
        hpos = [0] + [hs[i - 1] + hs[i] / 2. for i in range(1, len(layers))]

        self.hpos = np.array(hpos) - hm
        """Layer positions array, relative to the middle height of the composite"""

    def equilibrium_length(self, T):
        """Calculates the equilibrium length of the composite at a certain temperature.
        It is the average of all layers ideal length (uncoupled length), 
        weighted by each layer's elastic factor Eh"""
        n = 0
        d = 0
        for i, mat in enumerate(self.layers):
            # Ideal equilibrium length for mat layer
            mL = self.L0 * (1 + mat['fL'](T) / 100)
            mat['mL'] = mL
            # Weight that length by the elastic factor (E*h) of the layer
            n += mL * mat['Eh']
            # Add layer's Eh to the denominator of the average
            d += mat['Eh']
        return n / d

    def elastic_energy(self, inp, L):  # r
        """Calculates the elastic energy of the composite given a curvature radius and equilibrium length.
        `inp`: input paremeters list, [ curvature radius ]
        `L`  : equilibrium length of the composite
        The displacement of each layer towards its uncoupled length is calculated,
        and the elastic energies associated to all these displacements is summed up to the 
        returning result of the function.
         """
        r = inp[0]
        if abs(r) < 1:
            r = 1. * np.sign(r)
        # Calculate equilibrium length
        U = 0
        ar = abs(r)
        sgn = np.sign(r)
        for i, mat in enumerate(self.layers):
            # Length on curvature
            LR = (ar - sgn * self.hpos[i]) * L / ar
            # Displacement from equilibrium length
            dL = LR - mat['mL']
            # Add to energy
            u = mat['Eh'] * (dL**2)
            # print 'dL',mat['name'],dL,u
            U += u * np.sign(dL)
        # print r,abs(U)
        return abs(U)

    def simulation(self):
        """Perform flexure simulation. Returns:
        vT, flex, length
        vT: temperature array
        flex: flexure values array, as a function of vT
        length: composite equilibrium length array, as a function of vT"""
        curv = [100]
        length = []
        for T in self.vT:
            L = self.equilibrium_length(T)
            length.append(L)
            # Explore positive and negative curvature energies
            ePos = self.elastic_energy([10000.], L)
            eNeg = self.elastic_energy([-10000.], L)
            # Choose a starting curvature with the most favorable sign
            r0 = abs(curv[-1])
            if r0 < 1:
                r0 = 100
            r0 = r0 * np.sign(eNeg - ePos)
            # Minimize energy
            xopt, fopt, iter, funcalls, warnflag = fmin(self.elastic_energy, [r0], args=(L,),
                                                        disp=True, full_output=True)
            logging.debug('%s %s %s', T, xopt, fopt)
            curv.append(xopt[0])
        curv.pop(0)
        length = np.array(length)
        curv = np.array(curv)
        # Calculate vertical displacement of the middle point (flexure)
        flex = (abs(curv) - np.sqrt(curv**2 - (length / 2)**2)) * np.sign(curv)
        logging.debug('%s %s %s', self.vT, flex, length)
        return self.vT, flex, length


class SimFlexPlugin(plugins.DatasetPlugin):

    """Simlate a flexure curve starting from up to three dilatation curves"""
    # tuple of strings to build position on menu
    menu = ('Misura', 'Flex simulation')
    # internal name for reusing plugin later
    name = 'SimFlex'
    # string which appears in status bar
    description_short = 'Simulate a flexure curve from two dilatation curves'

    # string goes in dialog box
    description_full = ('Simulate a flexure curve from two dilatation curves')

    def __init__(self, ds0='', T0='', E0=200, h0=2,
                 ds1='', T1='', E1=300, h1=1,
                 ds2='', T2='', E2=400, h2=5,
                 L0=80, num=100, ds_out='simflex'):
        """Define input fields for plugin."""
        self.fields = [
            plugins.FieldDataset(
                'ds0', 'Top layer (L0) dilatation curve', default=ds0),
            plugins.FieldDataset(
                'T0', 'Top layer (L0) temperature curve', default=T0),
            plugins.FieldFloat('E0', 'L0 Elasticity Modulus', default=E0),
            plugins.FieldFloat('h0', 'L0 Thickness', default=h0),

            plugins.FieldDataset(
                'ds1', 'Second layer (L1) dilatation curve', default=ds1),
            plugins.FieldDataset(
                'T1', 'Second layer (L1) temperature curve', default=T1),
            plugins.FieldFloat('E1', 'L1 Elasticity Modulus', default=E1),
            plugins.FieldFloat('h1', 'L1 Thickness', default=h1),

            plugins.FieldDataset(
                'ds2', 'Third layer (L2) dilatation curve', default=ds2),
            plugins.FieldDataset(
                'T2', 'Third layer (L2) temperature curve', default=T2),
            plugins.FieldFloat('E2', 'L2 Elasticity Modulus', default=E2),
            plugins.FieldFloat('h2', 'L2 Thickness', default=h2),

            plugins.FieldFloat(
                'L0', 'Sample Starting length (rods inter-axis)', default=L0),
            plugins.FieldInt(
                'num', 'Number of flexure points to generate ', default=num),
            plugins.FieldDataset(
                'ds_out', 'Output dataset name', default=ds_out),
        ]

    def getDatasets(self, fields):
        """Returns single output dataset (self.ds_out).
        This method should return a list of Dataset objects, which can include
        Dataset1D, Dataset2D and DatasetText
        """
        # raise DatasetPluginException if there are errors
        if fields['ds_out'] == '':
            raise plugins.DatasetPluginException('Invalid output dataset name')
        if fields['ds_out'] in [fields['ds0'], fields['ds1'], fields['ds2']]:
            raise plugins.DatasetPluginException(
                'Input and output datasets cannot be the same.')
        # make a new dataset with name in fields['ds_out']
        self.ds_out = plugins.Dataset1D(fields['ds_out'])
        # Automatic temperature output dataset
        self.ds_T = plugins.Dataset1D(fields['ds_out'] + '_T')
        # Automatic equilibrium length output dataset
        self.ds_len = plugins.Dataset1D(fields['ds_out'] + '_L')
        # return list of datasets
        return [self.ds_out, self.ds_T, self.ds_len]

    def updateDatasets(self, fields, helper):
        """Do flex simulation.
        This function should *update* the dataset(s) returned by getDatasets
        """
        # TODO: se le informazioni sui layer potrebbero essere caricate direttamente dai file di test.
        # get the input datasets - helper provides methods for getting other
        # datasets from Veusz
        ds0 = helper.getDataset(fields['ds0'])
        x0 = numpy.array(ds0.data)
        ds1 = helper.getDataset(fields['ds1'])
        x1 = numpy.array(ds1.data)
        dT0 = helper.getDataset(fields['T0'])
        T0 = numpy.array(dT0.data)
        dT1 = helper.getDataset(fields['T1'])
        T1 = numpy.array(dT1.data)
        NL = 2
        # Optional third layer
        if fields['ds2'] != '':
            ds2 = helper.getDataset(fields['ds2'])
            x2 = numpy.array(ds2.data)
            dT2 = helper.getDataset(fields['T2'])
            T2 = numpy.array(dT2.data)
            NL = 3
        # Check dimensions of the input datasets
        if x0.ndim * x1.ndim * T0.ndim * T1.ndim != 1 or (NL == 3 and x2.ndim * T2.ndim != 1):
            raise DatasetPluginException(
                "simflex only accepts 1 dimension arrays.")
        # Build interpolating functions for dilatations
        fL0 = interpolate.interp1d(T0, x0)
        fL1 = interpolate.interp1d(T1, x1)
        fL2 = lambda a: 0
        if NL == 3:
            fL2 = interpolate.interp1d(T2, x2)
        # Temperature boundaries
        maxT = max(max(T0), max(T1))
        minT = min(min(T0), min(T1))
        # Setup the layers
        lay0 = {'E': fields['E0'],
                'h': fields['h0'],
                'fL': fL0,
                'name': 'top'
                }
        lay0['Eh'] = lay0['E'] * lay0['h']
        lay1 = {'E': fields['E1'],
                'h': fields['h1'],
                'fL': fL1,
                'name': 'second'
                }
        lay1['Eh'] = lay1['E'] * lay1['h']
        layers = [lay0, lay1]
        lay2 = {'E': fields['E2'],
                'h': fields['h2'],
                'fL': fL2,
                'name': 'third'
                }
        lay2['Eh'] = lay2['E'] * lay2['h']
        if NL == 3:
            layers.append(lay2)
        # Do the simulation
        sim = SimFlex(layers, fields['L0'], minT, maxT, fields['num'])
        vT, disp, length = sim.simulation()
        # Record output data
        self.ds_out.update(data=disp)
        self.ds_T.update(data=vT)
        self.ds_len.update(data=length)
        return [self.ds_out, self.ds_T, self.ds_len]

plugins.datasetpluginregistry.append(SimFlexPlugin)
