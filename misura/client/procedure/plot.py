#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Plot preview for thermal cycle."""
from misura.canon.logger import Log as logging
import numpy as np
from numpy import array
from .. import _
from ..graphics.plot import VeuszPlot



class ThermalCyclePlot(VeuszPlot):

    """Simple plot for thermal cycle preview"""

    @classmethod
    def setup(cls, cmd, graph='/time/time',
              T='tc', R='tc1',
              xT='x', yT='y', aT='y',
              xR='x1', yR='y1', aR='y1'):
        """Setup a ThermalCyclePlot on `graph` destination"""
        cmd.SetData(xT, [])
        cmd.SetData(yT, [])
        cmd.SetData(xR, [])
        cmd.SetData(yR, [])

        # Temperature
        cmd.To(graph)
        cmd.Add('xy', name=T)
        cmd.Add('axis', name=aT, direction='vertical')
        cmd.Set(aT + '/autoRange', '+10%')
        cmd.Set(T + '/xData', xT)
        cmd.Set(T + '/yData', yT)
        cmd.Set(T + '/yAxis', aT)

        # Rate
        cmd.To(graph)
        cmd.Add('xy', name=R)
        cmd.Add('axis', name=aR, direction='vertical')
        cmd.Set(aR + '/autoRange', '+10%')
        cmd.Set(R + '/xData', xR)
        cmd.Set(R + '/yData', yR)
        cmd.Set(R + '/yAxis', aR)

        # Axis
        cmd.To(graph)
        cmd.Set('x/label', str(_("Time (min)")))
        cmd.Set(aT + '/label', str(_("Temperature (\deg C)")))
        cmd.Set(aT + '/Label/color', 'red')
        cmd.Set(T + '/MarkerFill/color', 'red')
        cmd.Set(T + '/PlotLine/color', 'red')

        cmd.Set(aR + '/label', str(_("Rate (\deg C/min)")))
        cmd.Set(aR + '/Label/color', 'blue')
        cmd.Set(aR + '/otherPosition', 1)
        cmd.Set(R + '/thinfactor', 2)
        cmd.Set(R + '/PlotLine/color', 'blue')
        cmd.Set(R + '/MarkerFill/color', 'blue')

    def __init__(self, parent=None):
        VeuszPlot.__init__(self, parent=parent)
        self.set_doc()
        ThermalCyclePlot.setup(self.cmd)
        self.plot.setPageNumber(2)

    @classmethod
    def importCurve(cls, cmd, crv, graph='/time/time', xT='x', yT='y', xR='x1', yR='y1'):
        cmd.To(graph)
        trs = array(crv).transpose()
        x = trs[0].transpose() / 60.
        y = trs[1].transpose()
        cmd.SetData(xT, x)
        cmd.SetData(yT, y)
        if len(y) > 1:
            y1 = np.diff(y) / np.diff(x)
            y1 = array([y1, y1]).transpose().flatten()
            x1 = array([x, x]).transpose().flatten()[1:-1]
            logging.debug('%s %s', 'x1', x1)
            logging.debug('%s %s', 'y1', y1)
            cmd.SetData(yR, y1)
            cmd.SetData(xR, x1)
        else:
            cmd.SetData(yR, [])
            cmd.SetData(xR, [])
        if len(x) > 25:
            cmd.Set('/time/time/tc/marker', 'none')
            cmd.Set('/time/time/tc1/marker', 'none')

    def setCurve(self, crv):
        if len(crv) == 0:
            self.hide()
            return False
        ThermalCyclePlot.importCurve(self.cmd, crv)
        self.fitSize()
        self.plot.actionForceUpdate()
        return True
    