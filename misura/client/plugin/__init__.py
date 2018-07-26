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
from FFTPlugin import FFTPlugin

# Misura specific plugins
from MakeDefaultDoc import MakeDefaultDoc, makeDefaultDoc
from InitialDimensionPlugin import InitialDimensionPlugin
from PercentPlugin import PercentPlugin
from UnitsConverterTool import UnitsConverterTool
from CalibrationFactorPlugin import CalibrationFactorPlugin
from ThermalCyclePlugin import ThermalCyclePlugin, drawCycleOnGraph
from ShapesPlugin import ShapesPlugin
from MotorCorrectionPlugin import MotorCorrectionPlugin
from SimFlexPlugin import SimFlexPlugin
from ArrangePlugin import ArrangePlugin, save_plot_style_in_dataset_attr
from ReportPlugin import ReportPlugin
from ViscosityPlugin import ViscosityPlugin, viscosity_calc

from SurfaceTensionPlugin import SurfaceTensionPlugin



# FIELDS
from FieldConfigurationProxy import FieldConfigurationProxy
from FieldMisuraNavigator import FieldMisuraNavigator


# Install 3rd-party plugins
from utils import OperationWrapper
import veusz.plugins as plugins
    
