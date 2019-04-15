#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Wizard: option's panel component for prototyping"""
import os
from misura.client import _, conf
from misura.client import parameters as client_params 
from ..plugin import model_plugins
import re
from PyQt4 import QtGui, QtCore, QtSvg
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.option import match_node_path, from_column
from ..plugin import check_complete_shot

# Map filename: (range, keys)
# Ranges are in %, since we do not know the actual size of the label
positions = {'Gembarovic2D': [(0, 0, 100,100, ['jg2d_diameter', 'jg2d_thickness', 
                                               'jg2d_guessIrradiatedOuter', 'jg2d_guessViewedOuter',
                                               'jg2d_optimizeIrradiatedOuter', 'jg2d_optimizeViewedOuter']), ],
             'InPlane': [(0, 0, 100,100, ['inpl_diameter', 'inpl_thickness', 'inpl_guessIrradiatedOuter', 
                                          'inpl_guessIrradiatedInner', 'inpl_guessViewedOuter',
                                          'inpl_optimizeIrradiatedOuter', 'inpl_optimizeIrradiatedInner', 
                                          'inpl_optimizeViewedOuter']), ],
             'TwoLayers': [],
             'ThreeLayers': [],
    }

class FlashWizardSchematics(QtSvg.QSvgWidget):
    selected_keys = QtCore.pyqtSignal(list)
    def __init__(self, cfg, parent=None):
        """`cfg` configuration proxy"""
        super(FlashWizardSchematics, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(_('Click here to hide/show geometrical\nconfiguration options'))
        self.cfg = cfg
        self.setMaximumSize(500, 500)
        
        
        model = self.cfg.root.flash.measure['fitting']
        filename = os.path.join(client_params.pathArt, 
                                'flash_{}_schema.svg'.format(model))
        self.svg = open(filename, 'rb').read()
        self.keywords = re.findall('#:\w+:#', self.svg)
        self.active=False
        self.refresh()
        
    def refresh(self):
        from misura.client.live import registry
        svg = self.svg[:]
        for key in self.keywords:
            nkey = key[2:-2]
            opt = self.cfg.gete(nkey)
            val = self.cfg[nkey]
            svg = svg.replace(key, '{}: {:.4f}'.format(opt['name'], 
                                                 val))
            sig = 'client_changed_{}()'.format(self.cfg.plain_kid(nkey))
            registry.reconnect(sig, self.refresh)
        
        self.load(QtCore.QByteArray(svg))
        s = self.sizeHint()
        self.ratio = 1.*s.height()/s.width()
        h = self.heightForWidth(70)
        self.setMinimumSize(70, h)
    
    
    def heightForWidth(self, w):
        """NOTICE: called by resizeEvent. Never natively called!"""
        return int(w*self.ratio)
    
    def widthForHeight(self, h):
        return int(h/self.ratio)
    
    
    def resizeEvent(self, event):
        """Qt BUG: override resizeEvent to keep aspect ratio"""
        w = self.size().width()
        h = self.size().height()
        r = 1.*h/w
        if r>self.ratio:
            r = [w, self.heightForWidth(w)]
        else:
            r = [self.widthForHeight(h), h]
        r[0] = min(r[0], self.maximumWidth())
        r[1] = min(r[1], self.maximumHeight())
            
        self.resize(*r)
        event.accept()
        return None
    
    def mousePressEvent(self, event):
        if self.active:
            self.selected_keys.emit([])
        else:
            model = self.cfg.root.flash.measure['fitting']
            keys = positions[model][0][-1]
            self.selected_keys.emit(keys)
        self.active = not self.active
        return super(FlashWizardSchematics, self).mousePressEvent(event)
        # TODO: highlight specific options... 
        p = event.pos()
        x, y = p.x()*1./self.width(), p.y()*1./self.height()
        model = self.cfg.root.flash.measure['fitting']
        for x0,y0,x1,y1, keys in positions[model]:
            if x0<x and x<x1:
                print('XXXX', x0, x, x1)
                if y0<y and y<y1:
                    print('YYYYY', y0, y, y1)
                    self.selected_keys.emit(keys)
                    break
        
        return super(FlashWizardSchematics, self).mousePressEvent(event)

class FlashWizardPanel(QtGui.QTabWidget):
    results = False
    configuration = False
    permanent = False
    results2 = False
    
    
    def __init__(self, cfg, model_params_class, parent=None):
        """Generic options panel with Configuration/Results design.
        `node` Navigator node representing the shot"""
        super(FlashWizardPanel, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.model_params_class = model_params_class
        self.cfg = cfg
        desc = self.cfg.describe()
        vres = {}
        vconf = {}
        conf_keys = set()
        for field in ('sample','geometry','guess_names', 'optimization_names', 'runtime_options'):
            conf_keys.update(getattr(model_params_class,field,[]))
        res_keys = set()
        for field in ('result_names','introspection_names'):
            res_keys.update(getattr(model_params_class,field,[]))
            
        prefix = self.model_params_class.section+'_'
        for key, opt in desc.items():
            nkey = key.split('_')
            key_prefix = nkey[0]+'_'
            if key_prefix!=prefix:
                continue
            nkey = nkey[-1]
            if nkey in res_keys or 'Result' in opt['attr']:
                if not key.startswith(self.model_params_class.section):
                    continue
                vres[key] = opt
                continue
            if nkey in conf_keys:
                vconf[key] = opt
            else:
                print('FlashWizardPanel: Ignore key', key)
        
        self.conf_always_visible = {}
        
        for k in ('expPulse', 'jumpPoints', 'halftimeTimes', 'endTime', 'baselineShift'):
            k = prefix+k
            if k in self.cfg:
                self.conf_always_visible[k] = self.cfg.gete(k)
            if k in vconf:
                vconf.pop(k)
            if k in vres:
                vres.pop(k)
                
        # If recursion, remove non recursive
        dp = self.cfg['devpath']
        recursive = (dp.startswith('T') or dp.startswith('sample') or dp in ('flash', 'MAINSERVER'))
        if recursive:
            for handle in self.model_params_class.non_recursive:
                k = prefix+handle
                for group in (self.conf_always_visible, vconf, vres):
                    if k in group:
                        group.pop(k)
                        
                
        
        kw = {'fixed': True, 'flat': True}
        self.configuration = conf.Interface(self.cfg.root, self.cfg, vconf, **kw)
        self.permanent = conf.Interface(self.cfg.root, self.cfg, self.conf_always_visible, **kw)
        self.permanent.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Minimum)
        self.configuration.sectionsMap['Main'].layout().insertWidget(0, self.permanent)
        self.configuration.sectionsMap['Main'].layout().addStretch(100)
        self.results = conf.Interface(self.cfg.root, self.cfg, vres, **kw)
        self.select_configuration()
        
    def closeEvent(self, ev):
        ev.accept()
        self.clear()
        for obj in (self.permanent, self.configuration, self.results):
            obj.close()
            obj.deleteLater()
            
        
    def select_configuration(self, keys=[]):
        logging.debug('select_configuration', keys)
        if self.widget(0)!=self.configuration:
            self.insertTab(0, self.configuration, _('Configuration'))
            self.tabBar().hide()
        if keys is None:
            self.configuration.show_only_options(list(self.configuration.widgetsMap.keys()))
        else:
            self.configuration.show_only_options(keys)
        self.setCurrentIndex(0)
        self.currentChanged.emit(0)        
            
        
    def select_results(self, keys=[], tab=0):
        vres = {}
        for key in keys:
            if key in self.cfg:
                vres[key] = self.cfg.gete(key)
        if vres:  
            if self.results:
                self.results.close()
            kw = {'fixed': True, 'flat': True}  
            self.results = conf.Interface(self.cfg.root, self.cfg, vres, **kw)
        if self.widget(1)!=self.results:
            self.addTab(self.results, _('Results'))
            self.tabBar().show()
        # Keep anyway the config tab
        self.setCurrentIndex(tab)
        self.currentChanged.emit(tab)
        
    def show_object(self, obj, keys):
        # Remove any existing additional tab
        if self.count()==3:
            self.removeTab(2)
        if self.results2:
            self.results2.close()
        kw = {'fixed': True, 'flat': True} 
        vkeys = {k: obj.gete(k) for k in keys}
        self.results2 = conf.Interface(obj.root, obj, vkeys, **kw)
        prefix = obj.parent()['devpath']+'/'
        self.addTab(self.results2, prefix+obj['devpath'])
        self.tabBar().show()
        self.setCurrentIndex(2)
        self.currentChanged.emit(2)
        
        

def node_type(node=False, fullpath=False):
    node = node or fullpath
    if match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+/'):
        return 'model'
    if match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?/N[0-9]+$'):
        return 'shot'
    if bool(match_node_path(node, 'flash/sample[0-9]+/T(-)?[0-9]+(_[0-9]+)?$')):
        return 'segment'
    if bool(match_node_path(node, 'flash/sample[0-9]+$')):
        return 'sample'
    return 'test'

class FlashWizardEvaluation(QtGui.QSplitter):
    """Abstract class representing an evaluation panel. 
    Foundation for shot, segment, sample and test prototyping.
    """
    model_plugin_class = False
    panel = False
    schematics = False
    def __init__(self, node, navigator, plotwindow, parent=None):
        """Side panel showing both schematics and options panel.
        `node` Navigator node representing the shot"""
        super(FlashWizardEvaluation, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setOrientation(QtCore.Qt.Vertical)
        self.setMinimumWidth(400)
        self.navigator = navigator
        self.plotwindow = plotwindow
        self.node = node        
        self.cfg = node.get_configuration()
        self.model_name = self.cfg.root.flash.measure['fitting']
        
        for model_plugin_class in model_plugins:
            if model_plugin_class._params_class.section_name==self.model_name:
                self.model_plugin_class = model_plugin_class
                break
        self.model_params_class = model_plugin_class._params_class
        self.silent = True
        self.nosync = True
        self.model_plugin_instance = self.model_plugin_class(root=node, silent=self.silent)

        self.add_panel()
        self.add_schematics()
        
        self.setCollapsible(0, False)
        self.setCollapsible(1, True)
        self.setSizes([70, 30])
                
        self.plotwindow.sigWidgetClicked.connect(self.slot_clicked_plot)
        
    def closeEvent(self, ev):
        ev.accept()
        self.panel.close()
        self.panel.deleteLater()
        self.schematics.close()
        self.schematics.deleteLater()
        
    def add_panel(self):
        self.panel = FlashWizardPanel(self.cfg, self.model_plugin_class._params_class, parent=self)
        self.addWidget(self.panel) 
        self.panel.currentChanged.connect(self.slot_panel_tab_changed)
        return self.panel
        
    def add_schematics(self):
        self.schematics = FlashWizardSchematics(self.cfg, parent=self)
        self.schematics_widget = QtGui.QFrame()
        self.schematics_widget.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        lay = QtGui.QHBoxLayout()
        self.schematics_widget.setLayout(lay)
        lay.addStretch()
        lay.addWidget(self.schematics)
        lay.addStretch()
        self.addWidget(self.schematics_widget)
        self.schematics.selected_keys.connect(self.slot_clicked_schematics)
        return self.schematics
        
    def slot_panel_tab_changed(self, *a):
        """Switching between configuration/results panel tabs."""
        logging.debug('slot_panel_tab_changed', a)
        if self.panel.currentWidget()==self.panel.results:
            self.setSizes([100,0])
        else:
            self.setSizes([70,30])
        
    def slot_clicked_schematics(self, keys):
        """Schematics emits a list of involved keys"""
        logging.debug('slot_clicked_schematics', keys)
        self.panel.select_configuration(keys)
    
    def slot_clicked_plot(self, *a):
        wg = a[0]
        keys = None
        obj = False
        logging.debug('slot_clicked_plot', a, wg.typename, wg.path)
        if wg.typename == 'optionline':
            opts = wg.settings.intercept+wg.settings.slope+wg.settings.updaters
            if 'guessTmax' in opts:
                keys = ['guessTmax', 'optimizeTmax']
            elif 'guessBaselineShifted' in opts:
                keys = ['guessBaseline', 'optimizeBaseline', 'optimizeBaselineSlope']
            self.panel.setCurrentIndex(0)
        elif wg.typename == 'optionlabel' and self.panel.count()>1:
            # Move to Results tab
            self.panel.setCurrentIndex(1)
            logging.debug('slot_clicked_plot: move to results')
            return
        elif wg.typename == 'xy':
            page_type = node_type(fullpath=self.cfg['fullpath'])
            logging.debug('slot_clicked_plot on curve', page_type, self.cfg['fullpath'])
            # Ensure configuration is visible
            if page_type=='shot':
                if check_complete_shot(self.cfg, self.model_name):
                    logging.debug('slot_clicked_plot: clicked on curve from model page')
                    self.panel.select_results(tab=1)
                else:
                    logging.debug('slot_clicked_plot: clicked on curve from shot page')
                    self.panel.select_configuration(keys=None)
                return
            # Build a new panel with relevant object keys
            yds = wg.settings.yData
            obj,io = from_column(yds, self.cfg.root)
            ntype = node_type(obj['fullpath'])
            # Get the model obje
            if ntype=='shot':
                obj = obj.toPath(self.model_params_class.output_node)
                ntype = 'model'
            # Get result names
            if ntype=='model':
                keys = getattr(self.model_params_class,'result_names',[])
                keys = [self.model_params_class.section+'_'+k for k in keys]
            elif ntype == page_type:
                self.panel.select_results(tab=1)
                return
            else:
                # Generic tables
                keys = ['summary', self.model_params_class.handle]
                
            if keys:
                self.panel.show_object(obj, keys)
            logging.debug('slot_clicked_plot: clicked on subordered object', yds, obj['fullpath'], keys)
            return
        if keys:
            keys = [self.model_params_class.section+'_'+k for k in keys]
        # TODO: show relevant things depending on the clicked object
        logging.debug('slot_clicked_plot: select_configuration', a, wg.typename, wg.path, keys)
        self.panel.select_configuration(keys=keys)
        
  
class FlashWizardShotPrototype(FlashWizardEvaluation):
    model_plugin_class = False
    def __init__(self, node, navigator, plotwindow, parent=None):
        """Side panel showing both schematics and options panel.
        `node` Navigator node representing the shot"""
        super(FlashWizardShotPrototype, self).__init__(node, navigator, plotwindow, parent=None)
        self.setWindowTitle('Flash Wizard - Model prototyping (3)')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        
    def add_panel(self):
        """Initialize the plugin on shot's values before creating the panel"""
        self.model_plugin_instance.pre_apply(self.navigator.cmd, {'root': self.node, 'silent': self.silent,
                'nosync': self.nosync, 'preconf': self.cfg,
                'notify': True, 'parallel': False})
        return super(FlashWizardShotPrototype, self).add_panel() 
        
        
        
        