#!/usr/bin/python
"""  """
import sip
sip.setapi('QString', 2)
# Widget types
#from IconImage import *
from datapoint import DataPoint
from intercept import Intercept
from synaxis import SynAxis
from ImageReference import ImageReference

# Pure-Veusz Plugin (not Misura-aware)
from ZoomAxesPlugin import ZoomAxesPlugin
from InterceptPlugin import InterceptPlugin
from DeriveDatasetPlugin import DeriveDatasetPlugin
from CurveOperationPlugin import CurveOperationPlugin
from PlotPlugin import PlotDatasetPlugin, DefaultPlotPlugin
from SmoothDatasetPlugin import SmoothDatasetPlugin
from CoefficientPlugin import CoefficientPlugin
from SynchroPlugin import SynchroPlugin
from OverwritePlugin import OverwritePlugin
from ColorizePlugin import ColorizePlugin

# Misura specific plugins
from MakeDefaultDoc import MakeDefaultDoc, makeDefaultDoc
from InitialDimensionPlugin import InitialDimensionPlugin
from PercentilePlugin import PercentilePlugin
from UnitsConverterTool import UnitsConverterTool
from CalibrationFactorPlugin import CalibrationFactorPlugin
from ThermalCyclePlugin import ThermalCyclePlugin, drawCycleOnGraph
from ShapesPlugin import ShapesPlugin
from MotorCorrectionPlugin import MotorCorrectionPlugin
from SimFlexPlugin import SimFlexPlugin
from ArrangePlugin import ArrangePlugin
from ReportPlugin import ReportPlugin
from ViscosityPlugin import ViscosityPlugin, viscosity_calc


from SurfaceTensionPlugin import SurfaceTensionPlugin

# install 3rd-party plugins
import veusz.plugins as plugins
from misura.canon.plugin import veusz_toolsplugins
for plugin_extension in veusz_toolsplugins.itervalues():
    print 'Adding veusz_plugin', plugin_extension
    plugins.toolspluginregistry.append(plugin_extension)
    
from misura.canon.plugin import veusz_datasetplugins
for plugin_extension in veusz_datasetplugins.itervalues():
    print 'Adding veusz_plugin', plugin_extension
    plugins.datasetpluginregistry.append(plugin_extension)