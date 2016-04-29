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
from PlotPlugin import PlotDatasetPlugin
from DefaultPlotPlugin import DefaultPlotPlugin
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



# FIELDS
from FieldConfigurationProxy import FieldConfigurationProxy
from FieldMisuraNavigator import FieldMisuraNavigator


# Install 3rd-party plugins
from utils import OperationWrapper
import veusz.plugins as plugins
from misura.canon.plugin import veusz_toolsplugins
from misura.canon.plugin import veusz_datasetplugins


def create_veusz_plugin_class(plugin_extension, veusz_plugin_class):
    """Create a new class which inherits also from veusz_plugin_class"""
    new_name = plugin_extension.__name__ + 'Plugin'
    new_plugin_class = type(new_name, 
                (plugin_extension, OperationWrapper, veusz_plugin_class), {})
    setattr(plugins, new_name, new_plugin_class)
    return new_plugin_class
    
for plugin_extension in veusz_toolsplugins.itervalues():
    print 'Adding veusz_toolsplugin', plugin_extension
    new_plugin_class = create_veusz_plugin_class(plugin_extension, plugins.ToolsPlugin)
    plugins.toolspluginregistry.append(new_plugin_class)
    
    

for plugin_extension in veusz_datasetplugins.itervalues():
    print 'Adding veusz_datasetplugins', plugin_extension
    new_plugin_class = create_veusz_plugin_class(plugin_extension, plugins.DatasetPlugin)
    plugins.datasetpluginregistry.append(plugin_extension)
    
