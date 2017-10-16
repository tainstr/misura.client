#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import os
import datetime
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

import veusz
import veusz.plugins as plugins
import veusz.document as document
from veusz.document import CommandInterpreter

from .. import parameters as params
from FieldMisuraNavigator import FieldMisuraNavigator
import PlotPlugin
from ThermalCyclePlugin import drawCycleOnGraph
from utils import OperationWrapper
from report_plugin_utils import wr, render_meta
from veusz.document.operations import OperationWidgetDelete

from misura.client.clientconf import confdb

shape_names = {'m4': ('Sintering', 'Softening', 'Sphere', 'HalfSphere', 'Melting'),
               'm3': ('m3_Sintering', 'm3_Softening', 'm3_Sphere', 'm3_HalfSphere', 'm3_Melting'),
               'cen': ('cen_Sintering', 'cen_Deformation', 'cen_Emisphere', 'cen_Flow'),
               }

class ReportPlugin(OperationWrapper, plugins.ToolsPlugin):
    menu = ('Misura','Create Sample Report')
    # unique name for plugin
    name = 'Misura Report'
    # name to appear on status tool bar
    description_short = 'Create Report for Misura sample'
    # text to appear in dialog box
    description_full = 'Create a Report page for a Misura sample'
    templates = {}
    def __init__(self, sample=None, template_file_name='default.vsz', measure_to_plot='d'):
        """Make list of fields."""
        
        
        self.templates = {}
        for path in (params.pathArt, confdb['templates']):
            for fn in os.listdir(path):
                if not fn.endswith('.vsz'):
                    continue
                if not fn.startswith('report_'):
                    continue
                self.templates[fn] = path
        
        self.fields = [
            FieldMisuraNavigator(
                "sample", descr="Target sample:", depth='sample', default=sample),
            plugins.FieldText('measure_to_plot', 'Measure to plot', 
                              default=measure_to_plot),
            plugins.FieldCombo('template_file_name', 'Template filename', 
                               default=template_file_name, items=self.templates.keys()),
        ]

    def apply(self, command_interface, fields):
        doc = command_interface.document
        self.doc = doc
        command_interpreter = CommandInterpreter(doc)
        smp_path0 = fields['sample'].path
        smp_path = smp_path0.split(':')[1]
        vsmp = smp_path.split('/')
        smp_name = vsmp[-1]  # sample name
        smp_path = '/' + '/'.join(vsmp)  # cut summary/ stuff
        report_path = '/'+smp_path[1:].replace('/','_')+'_report'
        logging.debug(smp_path, smp_name, report_path)
        test = fields['sample'].linked
        from .. import filedata
        if not filedata.ism(test, filedata.LinkedMisuraFile):
            logging.debug(type(test), test)
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
            
        # Delete an existing report page to refresh on second run
        try:
            page = doc.resolveFullWidgetPath(report_path)
            op = OperationWidgetDelete(page)
            self.doc.applyOperation(op)
        except:
            pass
        measure = instr.measure
        sample = getattr(instr, smp_name)
        
        tpath = self.templates.get(fields['template_file_name'], False)
        if not tpath:
            d = fields['template_file_name']
        else:
            d = os.path.join(tpath, fields['template_file_name'])
        logo = os.path.join(params.pathArt, 'logo.png')
        tpl = open(d, 'rb').read().replace("u'report'", "u'{}'".format(report_path[1:]))
        command_interpreter.run(tpl)
        
        std = 'm4'
        if 'Standard: Misura 4' in tpl:
            std = 'm4'
        elif 'Standard: Misura 3' in tpl:
            std = 'm3'
        elif 'Standard: CEN/TS' in tpl:
            std = 'cen' 
        
        shapes = shape_names[std]
        
        page = doc.resolveFullWidgetPath(report_path)
        # Substitutions
        tc = kiln['curve']
        if len(tc) <= 8:
            drawCycleOnGraph(command_interface, tc, label=False, wdg=report_path +
                             '/lbl_tc', color='black', size='6pt', create=False)
        else:
            self.toset(page.getChild('lbl_tc'), 'hide', True)
        msg = wr('Measure', measure['name'])
        msg += '\\\\' + wr('Sample', sample['name'])
        self.toset(page.getChild('name'), 'label', msg)

        zt = test.conf['zerotime']
        zd = datetime.date.fromtimestamp(zt)
        dur = datetime.timedelta(seconds=int(measure['elapsed']))
        sdur = '{}'.format(dur)
        msg = wr('Date', zd.strftime("%d/%m/%Y"))
        msg += '\\\\' + wr('Duration', sdur)
        msg += render_meta(measure, inter='\\\\', zt=zt, full=True)
        self.toset(page.getChild('metadata'), 'label', msg)

# 		msg=render_meta(sample,'None')
# 		self.toset(page.getChild('shapes'),'label',msg)

        oname = measure.desc.get('operator', {'current': False})['current']
        if oname:
            self.toset(
                page.getChild('operator'), 'label', wr('Operator', oname))
        self.toset(
            page.getChild('uid'), 'label', wr('UID', measure['uid'], 34))
        self.toset(
            page.getChild('serial'), 'label', wr('Serial', test.conf['eq_sn']))
        self.toset(
            page.getChild('furnace'), 'label', wr('Furnace', kiln['ksn']))
        self.toset(
            page.getChild('logo'), 'filename', logo)

        msg = ''
        
        should_draw_shapes = True
        
        for sh in shapes:
            if not sample.has_key(sh):
                should_draw_shapes = False

        if should_draw_shapes:
            for sh in shapes:
                pt = sample[sh]
                shn = sample.gete(sh)['name']
                if pt['time'] in ['None', None, '']:
                    msg += 'None\\\\'
                    self.toset(page.getChild('lbl_' + sh), 'label', shn + ', ?')
                    continue
                image_reference = {'dataset': smp_path + '/profile',
                                   'filename': test.params.filename,
                                   'target': pt['time']}
                self.dict_toset(page.getChild(sh), image_reference)
                T = '%i{{\\deg}}C' % round(pt['temp'], 0)
                self.toset(page.getChild('lbl_' + sh), 'label', shn + ', ' + T)
                msg += T + '\\\\'
            self.toset(page.getChild('shapes'), 'label', msg)

            self.dict_toset(page.getChild('initial'), {'dataset': smp_path + '/profile',
                                                       'filename': test.params.filename, 'target': 0})
            T = doc.data.get(test.prefix + smp_path[1:] + '/T', False)
            if T is False:
                T = doc.data.get(test.prefix + 'kiln/T')
            T = T.data[0]
            self.toset(page.getChild('lbl_initial'), 'label',
                       'Initial, %.2f{{\\deg}}C' % T)

            #self.toset(page.getChild('standard'), 'label', wr(
            #    'Standard', sample['preset'], 50))

        # Thermal cycle plotting
        from ..procedure.thermal_cycle import ThermalCyclePlot
        from ..procedure.model import clean_curve
        graph = report_path + '/tc'
        p0 = test.prefix+sample['fullpath'][1:]
        cf = {'graph': graph, 'xT': p0+'reportxT',
              'yT': p0+'reportyT', 'xR': p0+'reportxR', 'yR': p0+'reportyR'}
        ThermalCyclePlot.setup(command_interface, with_progress=False, topMargin='4.7cm', **cf)
        tc = clean_curve(tc, events=False)
        ThermalCyclePlot.importCurve(command_interface, tc, **cf)
        cf = {'Label/font': 'Bitstream Vera Sans', 'Label/size': '6pt',
              'TickLabels/font': 'Bitstream Vera Sans',
              'TickLabels/size': '6pt'}
        self.dict_toset(doc.resolveFullWidgetPath(graph + '/y'), cf)
        self.dict_toset(doc.resolveFullWidgetPath(graph + '/y1'), cf)

        self.ops.append(document.OperationToolsPlugin(PlotPlugin.PlotDatasetPlugin(),
                                                      {'x': [test.prefix + 'kiln/T'],
                                                       'y': [smp_path0 + '/' + fields['measure_to_plot']],
                                                       'currentwidget': report_path + '/temp'}
                                                      ))
        self.apply_ops()

        self.dict_toset(doc.resolveFullWidgetPath(
            report_path + '/temp/ax:' + fields['measure_to_plot']), cf)

        self.apply_ops()

        command_interpreter.run("MoveToLastPage()")


plugins.toolspluginregistry.append(ReportPlugin)
