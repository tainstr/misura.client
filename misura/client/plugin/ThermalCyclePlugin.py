#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Draws Thermal Cycle in a text label."""
import veusz.plugins as plugins
import numpy
from traceback import print_exc
from FieldMisuraNavigator import FieldMisuraNavigator


def cycleFormat(t, T):
    """Convert a t,T cycle to a T,rate,stasis list for display"""
    t = numpy.array(t)
    T = numpy.array(T)
    dt = numpy.diff(t)
    dT = numpy.diff(T)
    rates = dT / dt
    istasis = numpy.where(rates < 0.01)[0]
    stasis = numpy.zeros(len(rates))
    for i in istasis:
        stasis[i] = dt[i]
    T = T[1:]
    return [T, rates, stasis]



def drawCycleOnGraph(cmd, tTc,  label='ThermalCycle', wdg=False, color='red', size='8pt'):
    if not wdg:
        wdg = 'tc' + label
    t = []
    T = []
    for v in tTc:
        vt, vT = v
        if isinstance(vT, str):
            continue
        t.append(vt)
        T.append(vT)
    nT, rates, stasis = cycleFormat(t, T)
    
    label1 = u'<math>\n'
    if label:
        label1 += u'<mfrac><mtext>{}</mtext>'.format(label)
    label1 +=u'<mtable columnlines="solid">\n'
    label1 += u'<mtr> <mtd>°C</mtd> <mtd>°C/m</mtd> <mtd>m</mtd> </mtr>\n'
    for i, iT in enumerate(nT):
        ir = rates[i]
        ist = stasis[i]
        iT = '%4.0f' % iT
        ir = '%3.1f' % (ir * 60)
        ist = '%3.1f' % (ist / 60)
        label1 += u'<mtr> <mtd>%-6s</mtd> <mtd>%-7s</mtd> <mtd>%-7s</mtd> </mtr>\n' % (iT, ir, ist)
    label1 += u'</mtable>\n'
    if label:
        label1 += u'</mfrac>\n'
    label1 += u'</math>'
    
    try:
        assert cmd.WidgetType(wdg)=='label'
    except:
        cmd.Add('label', name=wdg)
    
    cmd.To(wdg)
    cmd.Set('label', label1)
    cmd.Set('Text/color', color)
    cmd.Set('Text/size', size)
    cmd.Set('Text/font', 'Mono')


class ThermalCyclePlugin(plugins.ToolsPlugin):

    """Draw a thermal cycle legend"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Thermal legend')
    # unique name for plugin
    name = 'ThermalCycle'
    # name to appear on status tool bar
    description_short = 'Show thermal cycle legend'
    # text to appear in dialog box
    description_full = 'Draw thermal cycle legend on temperature and time graphs'

    def __init__(self, test=None):
        """Make list of fields."""
        self.fields = [
            FieldMisuraNavigator(
                "test", descr="Target test:", depth='test', default=test),
        ]

    def apply(self, interface, fields):
        test = fields['test'].linked
        # Horrific!
        from misura.client import filedata
        if not filedata.ism(test, filedata.LinkedMisuraFile):
            raise plugins.ToolsPluginException(
                'The target must be misura test file')
        # Search for test name
        uk = test.prefix + 'unknown'
        kiln = getattr(test.conf, 'kiln', False)
        if not kiln:
            raise plugins.ToolsPluginException('No Kiln configuration found.')
        instr = getattr(test.conf, test.instrument, False)
        if not instr:
            raise plugins.ToolsPluginException(
                'No measure configuration found.')

        sname = instr.measure.desc.get('name', {'current': uk})['current']
        tc = test.prefix + 'tc'
        interface.To('/time/time')
        drawCycleOnGraph(interface, kiln['curve'], label=sname, wdg=tc)
        interface.To('/temperature/temp')
        drawCycleOnGraph(interface, kiln['curve'], label=sname, wdg=tc)

plugins.toolspluginregistry.append(ThermalCyclePlugin)
