#!/usr/bin/python
# -*- coding: utf-8 -*-

import functools
import numpy as np

from veusz import document #NEEDED
from veusz.document.operations import OperationWidgetDelete, OperationWidgetAdd, OperationMultiple

from misura.canon.plugin import navigator_domains, NavigatorDomain, node
from misura.canon.logger import get_module_logging
from veusz.utils.search import iter_widgets
logging = get_module_logging(__name__)
from misura.canon.option import match_node_path

from misura.client.plugin import DefaultPlotPlugin, FFTPlugin
from misura.client.clientconf import confdb

from misura.client.widgets.active import extend_decimals
from misura.client import _
from misura.client import iutils

from PyQt4 import QtCore, QtGui
from ..widgets.runner import FlashModelNavigatorFragment
from ..widgets import FlashWizardGeneral, FlashWizardSelectShot, FlashWizardShotPrototype, FlashWizard

from ..plugin import model_plugins, models
from ..plugin import check_complete_sample, check_complete_segment, check_complete_shot, check_complete_test
from ..plugin.ModelPlotPlugin import ModelPlotPlugin
from ..plugin.SummaryPlotPlugin import SummaryPlotPlugin
from ..plugin.ShotPlotPlugin import ShotPlotPlugin
from ..widgets import ResultsAll, ResultsSingle

from thegram.flashline.convert import result_handles



def replace_model_rule(rule, node):
    sub0 = node.parent.path.split('/')
    sub = '/'.join(sub0[-3:])
    rule = rule.replace('sampleX/segmentX/shotX', sub)
    rule = rule.replace('modelX', node.name())
    return rule, sub


def replace_models(rule, measure=False):
    model = confdb['flash_model']
    fitting = confdb['flash_fitting']
    if measure:
        if measure.has_key('model'):
            model = measure['model'] or model
        if measure.has_key('fitting'):
            fitting = measure['fitting'] or fitting
    else:
        logging.warning('replace_models: no measure provided!')
    fitting = models.get(fitting, False)
    if fitting:
        fitting = fitting._params_class.handle
    else:
        fitting = '----------'
    rule = rule.replace('XmodelX', model)
    rule = rule.replace('XfittingX', fitting)
    logging.debug('replace_models', rule)
    return rule


load_model_rule = r'''flash/sampleX/segmentX/shotX/modelX/residuals$
flash/sampleX/segmentX/shotX/modelX_t$'''

laser_rule = r'''
flash/sampleX/segmentX/shotX/laser$
flash/sampleX/segmentX/shotX/laserFit$'''

def get_model_section(conf):
    plug = models[conf['model']]
    return plug._params_class.section




class FlashNavigatorDomain(FlashModelNavigatorFragment, NavigatorDomain):
    
    def __init__(self, *a, **k):
        FlashModelNavigatorFragment.__init__(self)
        NavigatorDomain.__init__(self, *a, **k)

    def check_node(self, node):
        if not node:
            return False
        return 'flash' in node.path

    def collect_dataset_names(self, node):
        dataset_names = []
        prefix = node.path.split('/')[0]
        if not ':' in prefix:
            prefix += ':'
        logging.debug('collect_dataset_names', prefix)
        for ds in self.navigator.doc.data.keys():
            if ds.startswith(prefix):
                dataset_names.append(ds)
        return dataset_names

    def change_page(self, base_page_name):
        base_page_name = base_page_name.replace('/', '')
        if base_page_name=='temperature':
            page_num = self.navigator.get_page_number_from_path(base_page_name)
            logging.debug('change_page', base_page_name, page_num)
        else:
            page_T = base_page_name + '_T' 
            page_t = base_page_name + '_t'
            page_num = self.navigator.get_page_number_from_path(page_T)
            if page_num < 0:
                page_num = self.navigator.get_page_number_from_path(page_t)
        if page_num >= 0:
            self.navigator.mainwindow.plot.setPageNumber(page_num)
            if hasattr(self.navigator.mainwindow.plot.parent(), 'fitSize'):
                self.navigator.mainwindow.plot.parent().fitSize()
            return True, self.doc.basewidget.children[page_num]

        return False, False

    def create_default_plot(self, node, plot_rule, load_rule='', 
                            time_plot=True, temp_plot=True, grid=False, title='', 
                            update=False, force=False,
                            plot_plugin_cls=DefaultPlotPlugin, 
                            option_label=False, view_model=False,
                            **plugin_kwargs):
        page = '/{}'.format(node.path.replace('/', '_'))
        if page.endswith(':flash'):
            page = '/temperature'
        logging.debug('create_default_plot', page)
        exists, pagewg = self.change_page(page)
        if exists and not update:
            if not force:
                r = QtGui.QMessageBox.question(None, _('Default plot already exists'),
                                               _(
                                                   'Requested plot already exists. Recreate it (Ok) \nor just switch to its page (Cancel)?'),
                                               QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
                if r == QtGui.QMessageBox.Cancel:
                    return False
            op = OperationWidgetDelete(pagewg)
            self.doc.applyOperation(op)
        if not exists and update and not force:
            return False
        rule = plot_rule
        if load_rule:
            rule += '\n' + load_rule
        self.navigator.load_rule(node, rule, overwrite=False)
        dataset_names = self.collect_dataset_names(node)
        if not len(dataset_names):
            logging.error('No dataset involved in page creation!', page)
            return False
        graphs = []
        grid = 'grid/' if grid else ''
        if page=='/temperature':
            graphs.append(page + '/temp')
        else:
            if temp_plot:
                graphs.append(page + '_T/' + grid + 'temp')
            if time_plot:
                graphs.append(page + '_t/' + grid + 'time')
        p = plot_plugin_cls()
        plugin_kwargs.update({'dsn': dataset_names,
                                     'rule': plot_rule,
                                     'graphs': graphs,
                                     'title': title.replace('_','\_'),
                                     'node': node})
        p.apply(self.navigator.cmd, plugin_kwargs)
        
        # Avoid updating the navigator on recursive update
        self._last_page_edited = page
        if (not update) or force:
            logging.debug('create_default_plot: switch to updated page', page)
            exists, pagewg = self.change_page(page)
        
        if temp_plot:
            plt = pagewg.getChild('temp')
        elif time_plot:
            plt = pagewg.getChild('time')
        if not plt:
            plt = pagewg.getChild('grid').getChild('time')
        
        option_dataset = False
        for ds in dataset_names:
            if ds.endswith('/raw'):
                option_dataset = ds
                
        # Add the option label
        if option_label and option_dataset:
            option_label['dataset'] = option_dataset
            op = OperationWidgetAdd(plt, 'optionlabel', **option_label)     
            self.doc.applyOperation(op)
        
        model_target_node = node
        if plot_plugin_cls==ModelPlotPlugin:
            model_target_node = self.model().tree.traverse(node.path).parent
        self.add_model_widgets(model_target_node, view_model, plt, option_dataset)
            
        return p.created

    def add_model_widgets(self, node, section, plt0, dataset):
        """Adds model widgets to plot `plt`"""
        if not (section and dataset):
            return False
        path = node.path+'/'+section+'_'
        kw = {'dataset': dataset}
        plt = 0
        for xy in plt0.children:
            if xy.typename=='xy':
                if node.path in xy.settings.yData:
                    plt = xy
                    break
        if not plt:
            logging.error('Cannot add model widgets to', plt0.path)
            return False
        ops = []
        # Baseline
        op = OperationWidgetAdd(plt, 'optionline', name='base', 
                                intercept=path+'guessBaselineShifted',
                                slope=path+'guessBaselineSlope',
                                updaters=path+'baselineShift',
                                legend=_('Base line'),
                                **kw)
        ops.append(op)
        
        
        # Tmax
        op = OperationWidgetAdd(plt, 'optionline', name='guessTmax',
                                slope=path+'guessBaselineSlope',
                                intercept=path+'guessTmax+'+path+'guessBaselineShifted',
                                legend=_('T max'),
                                **kw)     
        ops.append(op)
        
        # Start time
        op = OperationWidgetAdd(plt, 'optionline', name='jumpPoints',
                                intercept=path+'jumpPoints',
                                scale=0.001,
                                invert=True,
                                legend=_('Start time'),
                                **kw)     
        ops.append(op)
        
        # End time
        op = OperationWidgetAdd(plt, 'optionline', name='endTime',
                                intercept=path+'endTime',
                                scale=0.001,
                                invert=True,
                                legend=_('End time'),
                                **kw)     
        ops.append(op)
        op = OperationMultiple(ops, 'Add model widgets')
        self.doc.applyOperation(op)
        
        
        # Customize
        for name, color in (('base','blue'), ('guessTmax','red'),
                            ('jumpPoints', 'green'), ('endTime','magenta')):
            b = plt.getChild(name)
            b.settings.Line.color = color
            b.settings.Line.width = '1pt'
        return True

    def model_name(self, node):
        return node.linked.conf.flash.measure['fitting']

    @node
    def summary_plot(self, node, update=False, force=False):
        logging.debug('summary_plot', node.path, update, force)
        if node.path.endswith('/measure'):
            node = node.parent
        elif node.path == '0':
            node = node.get('flash')
        rule = confdb['flash_test_plot'].splitlines()
        remove_lines = []
        model_name = self.model_name(node)
        if model_name and check_complete_sample(node.get_configuration(), model_name):
            for line in rule:
                if 'XmodelX' in line:
                    remove_lines.append(line)
                    logging.debug('Test is complete. Removing legacy plot rule', line)
        map(rule.remove, remove_lines)
        rule = '\n'.join(rule)
        rule = replace_models(rule, node.linked.conf.flash.measure)
        created = self.create_default_plot(node, rule,
                                           title='Flash Test Summary',
                                           time_plot = False,
                                           update=update, force=force,
                                           plot_plugin_cls=SummaryPlotPlugin)
        return created

    @node
    def sample_plot(self, node, update=False, force=False):
        # TODO: ensure loaded datasets!
        logging.debug('sample_plot', node.path)
        opt = node.path+'/summary'
        rule = confdb['flash_sample_plot'].splitlines()
        remove_lines = []
        model_name = self.model_name(node)
        if model_name and check_complete_sample(node.get_configuration(), model_name):
            opt = node.path+'/'+models[model_name]._params_class.handle
            for line in rule:
                if 'XmodelX' in line:
                    remove_lines.append(line)
                    logging.debug('Sample is complete. Removing legacy plot rule', line)
        map(rule.remove, remove_lines)
        rule = '\n'.join(rule)
        rule = replace_models(rule, node.linked.conf.flash.measure)
        rule = rule.replace('sampleX', node.name())
        self.create_default_plot(node, rule, time_plot=False,
                                 title='Sample Summary for: ' + node.name(),
                                 update=update, force=force, 
                                 option_label={'option': opt, 
                                               'xPos': 0.01, 'yPos': 0.01, 'showName': False})
        return True

    @node
    def segment_plot(self, node, update=False, force=False):
        logging.debug('segment_plot', node.path)
        rule = replace_models(confdb['flash_segment_plot'], node.linked.conf.flash.measure)
        sub = '/'.join(node.path.split('/')[-2:])
        rule = rule.replace('sampleX/segmentX', sub)
        conf = node.get_configuration()
        xranges = ['Auto', 'Auto']
        hts = []
        bases = []
        deltas = []
        for shot in conf.devices:
            if 'halftime' in shot:
                hts.append(shot['halftime'])
            if 'base_halfTime' in shot:
                bases.append(shot['base_constant'])
                deltas.append(shot['base_guessTmax'])
        ht = max(hts)
        if ht>1e-5:
            v = ht*confdb['flash_plotHalfTimes']
            xranges = [-v/2., v*1.05]
            
        yranges = ['Auto', 'Auto']
        if bases:
            deltas = np.array(deltas)
            bases = np.array(bases)
            Tmaxes = bases+deltas
            margin = 0.2*max(deltas)
            base = min(bases)
            Tmax = max(Tmaxes)
            yranges = [float(base-margin), float(Tmax+margin)]    
        
            
        model_name = self.model_name(node)
        opt = node.path+'/summary'
        if model_name and check_complete_segment(node.get_configuration(), model_name):
            opt = node.path+'/'+models[model_name]._params_class.handle
        option_label={'option': opt, 'showName': False, 
                      'alignVert': 'top', 'xPos': 0.01, 'yPos': 0.99}
        c = self.create_default_plot(node, rule, temp_plot=False,
                                 title='Segment Summary for ' + sub,
                                 update=update,
                                 force=force,
                                 plot_plugin_cls=ShotPlotPlugin,
                                 xranges=xranges,
                                 yranges=yranges,
                                 option_label=option_label)
        cmd =self.navigator.cmd 
        cmd.To(c[0])
        cmd.Add('synaxis', name='sync')
        cmd.To('sync')
        cmd.Set('otherPosition', 0.1)
        g = self.doc.resolveFullWidgetPath(c[0])
        for i, curve in enumerate(iter_widgets(g, 'xy', 1)): 
            if curve and curve.name:
                cmd.Set('curve'+str(i), curve.name)
        
        return True

    @node
    def shot_plot(self, node, update=False, laser=False, force=False, view_model=False):
        logging.debug('shot_plot', node.path)
        rule = confdb['flash_shot_plot']
        if laser:
            rule += laser_rule
        rule = replace_models(rule, node.linked.conf.flash.measure)
        sub = '/'.join(node.path.split('/')[-3:])
        rule = rule.replace('sampleX/segmentX/shotX', sub)
        
        conf = node.get_configuration()
        
        yranges = ['Auto', 'Auto']
        if 'base_halfTime' in conf:
            base = conf['base_constant']
            delta = conf['base_guessTmax']
            Tmax = base+delta
            margin = 0.1*delta
            yranges = [base-margin, Tmax+margin]
        
        xranges = ['Auto','Auto'] 
        if conf and 'halftime' in conf:
            ht = conf['halftime']
            if ht>0:
                v = ht*confdb['flash_plotHalfTimes']
                xranges = [-v/2., v*1.05]
        else:
            logging.debug('NO HALFTIME!', conf, conf.keys())
        logging.debug('XRANGES', conf, xranges)
        label = ''
        for opt in ('temperature','setpoint', 'halftime', 'clarkTaylor','parker','reference',
                    'jg2d_diffusivity','inpl_diffusivity'):
            label+=node.path+'/'+opt+','
        option_label={'option': label[:-1], 'showName': True, 
                      'alignVert': 'top', 'xPos': 0.01, 'yPos': 0.99}
        self.create_default_plot(node, rule, temp_plot=False,
                                 title='Shot Summary for ' + sub,
                                 update=update, force=force,
                                 plot_plugin_cls=ShotPlotPlugin,
                                 xranges=xranges,
                                 yranges=yranges,
                                 option_label=option_label,
                                 view_model=view_model)
        return True
    
    @node
    def laser_plot(self, node, update=False):
        return self.shot_plot(node, update=update, laser=True)
    
    @node
    def shot_fft_plot(self, node, update=False):
        logging.debug('shot_fft_plot', node.path)
        self.navigator.load_rule(node, node.path[2:]+'/raw$', overwrite=False)
        dataset_names = self.collect_dataset_names(node)
        if not len(dataset_names):
            return False
        
        # Calculate or guess end time for shot
        end_time = 0
        conf = node.get_configuration()
        t = self.navigator.doc.data[node.path+'/raw_t'].data
        e = max(len(t), 50000)
        if conf and 'halftime' in conf:
            ht = conf['halftime']
            if ht>0:
                end_time = ht*confdb['flash_plotHalfTimes']
                
        if end_time:
            d = np.abs(t-end_time)
            e=np.where(d==min(d))[0][0]
            e = int(e)
        else:
            # GUESS end time
            logging.debug('NO HALFTIME!', conf, conf.keys())
            raw = self.navigator.doc.data[node.path+'/raw'].data
            e = np.where(raw==max(raw))[0][0]*2
            
        # Calculate FFT dataset
        f = node.path+'/raw/fft'
        ft = node.path+'/raw/fft_t'
        p = FFTPlugin()
        fields = dict(ds_in=node.path+'/raw', ds_t=node.path+'/raw_t', start_index=0, end_index=e, ds_out=f,
                      min_freq=1, max_freq=500)
        op = document.OperationDatasetPlugin(p, fields)
        self.doc.applyOperation(op)
        # Update children
        node.children
        
        # Plot
        page = '/{}:fft'.format(node.path.replace('/', '_'))
        exists, pagewg = self.change_page(page)
        if exists and not update:
            r = QtGui.QMessageBox.question(None, _('Default plot already exists'),
                                           _(
                                               'Requested plot already exists. Recreate it (Ok) \nor just switch to its page (Cancel)?'),
                                           QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
            if r == QtGui.QMessageBox.Cancel:
                return False
            op = OperationWidgetDelete(pagewg)
            self.doc.applyOperation(op)
        if not exists and update:
            return False
        
        
        p = DefaultPlotPlugin()
        p.apply(self.navigator.cmd, {'dsn': [f],
                                     'rule': '',
                                     'graphs': [page + '_t/time'],
                                     'title': 'FFT for shot '+node.path,
                                     'node': node})
        xaxis = self.doc.resolveFullWidgetPath(page + '_t/time/x')
        op = document.OperationSettingSet(
                xaxis.settings.getFromPath(['label']), 'Frequency (Hz)')
        self.doc.applyOperation(op)
        # Avoid updating the navigator on recursive update
        self._last_page_edited = page
        if not update:
            self.change_page(page)
        return True

    @node
    def model_plot(self, node, update=False, force=False, view_model=False):
        # TODO: unplot raw curve
        logging.debug('model_plot', node.path, node.parent)
        load_rule = load_model_rule
        
        conf = node.get_configuration()
        if not conf:
            return False
        
        sec = get_model_section(conf)
        if view_model is True:
            view_model = sec
        ep = sec+'_expPulse'
        plot_rule = confdb['flash_model_plot']
        if ep in conf and conf[ep]:
            load_rule += laser_rule
            plot_rule += laser_rule
            
        load_rule, sub = replace_model_rule(load_rule, node)
        plot_rule, sub = replace_model_rule(plot_rule, node)
        
        m = conf['model']
        label = ''
        if m=='TwoLayers':
            label += '{n}/{s}_diffusivity1,{n}/{s}_diffusivity2'
        elif m=='ThreeLayers':
            label += '{n}/{s}_diffusivity1,{n}/{s}_diffusivity2,{n}/{s}_diffusivity3'
        else:
            label+='{n}/{s}_diffusivity'
            
        label += ',{n}/{s}_reference,{n}/{s}_diffusivityRef'
            
        label = label.format(n=node.path, s=sec)

        option_label={'option': label, 'showName': True, 
                      'alignVert': 'top', 'xPos': 0.01, 'yPos': 0.99}
        
        yranges = ['Auto', 'Auto']
        if 'base_halfTime' in conf.parent():
            base = conf.parent()['base_constant']
            delta = conf.parent()['base_guessTmax']
            Tmax = base+delta
            margin = 0.1*delta
            yranges = [base-margin, Tmax+margin]
        
        self.create_default_plot(node, plot_rule,
                                 load_rule=load_rule,
                                 temp_plot=False, grid=True,
                                 title='Model plot '+sub,
                                 update=update, force=force,
                                 plot_plugin_cls=ModelPlotPlugin,
                                 option_label=option_label,
                                 view_model=view_model,
                                 yranges=yranges)
        return True

    def double_clicked(self, node, update=False):
        logging.debug('double_clicked', node.path)
        if match_node_path(node, 'flash$'):
            return self.summary_plot(node, update=update)
        if match_node_path(node, 'flash/sample[0-9]+$'):
            return self.sample_plot(node, update=update)
        if match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?$'):
            return self.segment_plot(node, update=update)
        if match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+$'):
            return self.shot_plot(node, update=update)
        # Going below to models
        if (not node.ds) and match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+/'):
            return self.model_plot(node, update=update)
        return False
    
    @node
    def results_all(self, node=False):
        k = 'ResultsAll:'+node.path
        w = self.navigator.show_widget_key(k)
        if w:
            return w
        
        wg = ResultsAll(node, node.get_configuration(), self.navigator)
        win = self.navigator.show_widget(wg, k)
        return wg
        
    @node
    def results_single(self, node=False):
        cfg = node.get_configuration()
        diffusivity = ResultsSingle.get_model_diffusivity_name(cfg.parent().measure['fitting'])
        if not diffusivity:
            diffusivity = confdb['flash_model']
        
        k = 'ResultsSingle:{}:{}'.format(diffusivity, node.path)
        w = self.navigator.show_widget_key(k)
        if w:
            return w
        wg = ResultsSingle(node, cfg, diffusivity, self.navigator)
        win = self.navigator.show_widget(wg, k, 600, 300)
        return wg
    
    def set_reference_diffusivity(self, samples, value):
        for sample in samples:
            sample['diffusivityFile'] = value
      
    @node  
    def create_reference_material_menu(self, node=False, menu=False):
        menu.clear()
        # Detect measure node
        if node.name() == 'measure':
            node = node.parent
        # Detect flash node and build samples list 
        if node.name() == 'flash':
            samples = []
            for name, child in node.items():
                if name.startswith('sample'):
                    samples.append(child)
        # A sample node is taken directly
        else:
            samples = [node]
        # Convert nodes to configurations
        samples = [s.get_configuration() for s in samples]
        opt = samples[-1].gete('diffusivityFile')
        curs = list(set([s['diffusivityFile'] for s in samples]))
        for val in opt['options']:
            a = menu.addAction(val, functools.partial(self.set_reference_diffusivity, 
                                                      samples, val))
            if len(curs)==1 and val==curs[0]:
                a.setCheckable(True)
                a.setChecked(True)

    @node  
    def create_table_to_plot_menu(self, node=False, menu=False):
        menu.clear()
        conf = node.get_configuration()
        path = conf['fullpath']
        if not path.endswith('/'): path+='/'
        dataset = False
        for name, ds in self.doc.data.items():
            if ds.linked == node.linked:
                dataset = name
                break
        if not dataset:
            logging.error('Could not find a valid dataset in the document', path, 
                          node.linked.filename)
            return False
        for handle,title,foo in [('summary','Summary',0)]+result_handles+[('gembarovic','Gembarovic 2D',0),
                                                ('inplane','InPlane',0)]:
            if confdb.rule_opt_hide(path+handle):
                continue
            if handle not in ('summary', 'inplane','gembarovic'):
                handle += 's'
            if handle not in conf:
                continue
            a = menu.addAction(title, functools.partial(self.add_option_label, 
                                                      path+handle, dataset))
               
    def add_option_label(self, option, dataset):
        logging.debug('add_option_label', option, dataset)
        page = self.doc.getPage(self.navigator.mainwindow.plot.getPageNumber())
        graph = iutils.searchFirstOccurrence(page, 'graph')
        op = OperationWidgetAdd(graph, 'optionlabel', dataset=dataset, option=option)
        self.doc.applyOperation(op)
        
        
    ######################################
    # Menus
    ###################
        
    def create_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_T), 
                        self.navigator, 
                        self.results_single,
                        context=QtCore.Qt.WidgetWithChildrenShortcut)

    def add_models(self, menu, label, callback, models=False, icon='', **kw):
        """Add all model plugins launch actions to `menu`, with suffix `label`,
        and function callback `callback`"""
        if icon:
            icon = '_'+icon
        for model in model_plugins:
            if models and (model._params_class.section_name not in models):
                continue
            sec = model._params_class.section_name
            act = menu.addAction(iutils.theme_icon('flash_'+sec+icon), label + ' ' + sec, 
                           functools.partial(self._model_callback, callback, model, **kw))
        return True

    def build_file_menu(self, menu, node):
        if not node.children.has_key('flash'):
            return False
        menu.addAction(iutils.theme_icon('help-about'), _('Summary plot'), self.summary_plot)
        node = node.get('flash')
        self.add_models(menu, _('Recursive'), self.run_recursive_plugin_file, 
                        self.get_models(node), node=node)
        menu.addAction(iutils.theme_icon('flash_wizard'),_('Wizard'), self.wizard)
        return True
    
    def get_models(self, node):
        measure = node.get_configuration().root.flash.measure
        if not measure['fitting']:
            return False
        return [measure['fitting']]
    
    
    @node
    def wizard(self, node=False):
        self.wizard_wg = FlashWizard(node, self)

    def add_group_menu(self, menu, node):
        if match_node_path(node, 'flash/measure$'):
            return False
        # INSTRUMENT
        if match_node_path(node, 'flash$'):
            menu.addAction(iutils.theme_icon('help-about'), _('Summary plot'), self.summary_plot)
            self.add_models(menu, _('Recursive'),
                            self.run_recursive_plugin_file, 
                            models=self.get_models(node),
                            icon='recurse')
            self.ref_menu_flash = menu.addMenu(_('Set reference material'))
            self.ref_func_flash = functools.partial(self.create_reference_material_menu, node, 
                                                    self.ref_menu_flash)
            self.ref_menu_flash.aboutToShow.connect(self.ref_func_flash)
            menu.addAction(iutils.theme_icon('flash_wizard'), _('Wizard'), self.wizard)
        # MEASURE
        elif match_node_path(node, 'flash/measure$'):
            menu.addAction(iutils.theme_icon('help-about'), _('Summary plot'), self.summary_plot)
            fnode = node.parent
            self.add_models(menu, _('Recursive'), self.run_recursive_plugin_file, 
                    models=self.get_models(fnode),
                    icon='recurse', 
                    node=fnode)
            self.ref_menu_measure = menu.addMenu(_('Set reference material'))
            self.ref_func_measure = functools.partial(self.create_reference_material_menu, node, 
                                                      self.ref_menu_measure)
            self.ref_menu_measure.aboutToShow.connect(self.ref_func_measure)
            menu.addAction(iutils.theme_icon('flash_wizard'), _('Wizard'), self.wizard)
        # SEGMENTS
        elif match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?$'):
            menu.addAction(iutils.theme_icon('help-about'),_('Segment plot'), self.segment_plot)
            self.add_models(menu, _('Recursive'),
                            self.run_recursive_plugin_segment, 
                            models=self.get_models(node),
                            icon='recurse')
            self.opt_label_menu = self.add_table_to_plot_menu(menu, node)
            menu.addAction(iutils.theme_icon('flash_wizard'), _('Wizard'), self.wizard)
        # SHOTS
        elif match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+$'):
            menu.addAction(iutils.theme_icon('help-about'), _('Shot plot'), self.shot_plot)
            menu.addAction(_('Laser plot'), self.laser_plot)
            menu.addAction(iutils.theme_icon('flash_FFT'), _('FFT plot'), self.shot_fft_plot)
            menu.addAction(_('Run Baseline Correction'), self.run_baseline)
            self.add_models(menu, _('Run'), self.run_model_plugin, 
                            models=self.get_models(node), 
                            node=node)
            menu.addAction(iutils.theme_icon('flash_wizard'), _('Wizard'), self.wizard)
        # MODELS
        elif (not node.ds) and match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+/'):
            conf = node.get_configuration()
            if not conf:
                logging.error('Node has no configuration', node.path)
                return
            if 'model' not in conf:
                logging.debug('Node has no model key:', id(node), node.path, conf['fullpath'], conf.keys(), conf.desc)
                return
            model = conf['model']
            menu.addAction(iutils.theme_icon('help-about'), _('Model plot'), self.model_plot)
            self.add_models(menu, _('Repeat'), self.run_model_plugin, models=[model], 
                            icon='repeat',
                            node=node)
            menu.addAction(iutils.theme_icon('flash_wizard'), _('Wizard'), self.wizard)

    def add_sample_menu(self, menu, node):
        menu.addAction(iutils.theme_icon('help-about'), _('Sample Plot'), self.sample_plot)
        menu.addAction(iutils.theme_icon('flash_results'),_('Results table'), self.results_single)
        self.ref_menu = menu.addMenu(_('Set reference material'))
        self.ref_func = functools.partial(self.create_reference_material_menu, node, self.ref_menu)
        self.ref_menu.aboutToShow.connect(self.ref_func)
        menu.addAction(_('All results table'), self.results_all)
        self.add_models(menu, _('Recursive'), self.run_recursive_plugin_sample, 
                        models=self.get_models(node), 
                        icon='recurse')
        self.opt_label_menu = self.add_table_to_plot_menu(menu, node)
        menu.addAction(iutils.theme_icon('flash_wizard'),_('Wizard'), self.wizard)
        
    def add_table_to_plot_menu(self, menu, node):
        opt_label_menu = menu.addMenu(_('Table to plot'))
        opt_label_func = functools.partial(self.create_table_to_plot_menu, node, opt_label_menu)
        opt_label_menu.aboutToShow.connect(opt_label_func)
        return opt_label_menu
        
    def _model_callback(self, callback, model, *a, **kw):
        kw['plugin']=model
        callback(*a, **kw)


navigator_domains += [FlashNavigatorDomain]
