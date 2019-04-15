#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Wizard: progress component"""
from misura.client import _, iutils 
from functools import partial
from PyQt4 import QtGui, QtCore
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from ..plugin import check_complete_sample, check_complete_segment, check_complete_shot, check_complete_test
from .wizard_general import FlashWizardGeneral
from .wizard_select import FlashWizardSelectShot
from .wizard_shot import FlashWizardShotPrototype, FlashWizardEvaluation, node_type


shot_legend = _("""Click on schematics to show geometry settings.
Move plot lines to configure model parameters. 
Click anywhere in the plot to show all parameters.""")

segment_legend = _("""Click on a thermogram to see shot results.""")

sample_legend = _("""Click on segment points to show segment results.""")

test_legend = _("""Click on sample curve to show sample results.""")


class FlashWizardPushButton(QtGui.QPushButton):
    right_icon = False
    def __init__(self, *args, **kwargs):
        right_icon = kwargs.get('right_icon', None)
        if right_icon is not None:
            kwargs.pop('right_icon')
        self.right_icon = right_icon
        super(FlashWizardPushButton, self).__init__(*args, **kwargs)
        if not right_icon:
            return
        self._icon = self.icon()
        self._icon_size = self.iconSize()
        # remove icon
        self.setIcon(QtGui.QIcon())
        label_icon = QtGui.QLabel()
        label_icon.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        label_icon.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        lay = QtGui.QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.addWidget(label_icon, alignment=QtCore.Qt.AlignRight)
        label_icon.setPixmap(self._icon.pixmap(self._icon_size))
        
    def sizeHint(self):
        hint = QtGui.QPushButton.sizeHint(self)
        if not self.right_icon:
            return hint
        return QtCore.QSize(hint.width()+self._icon_size.width()+20, hint.height())
    
    def mousePressEvent(self, event):
        if event.button()==QtCore.Qt.RightButton:
            self.showMenu()
            return
        self.clicked.emit(False)
      


class FlashWizard(QtGui.QWidget):
    wizard_wg = False
    default_dock_visibility = [1, 0, 1, 1, 1, 1, 1]
    def __init__(self, node, domain, parent=None):
        super(FlashWizard, self).__init__(parent=parent)
        self.history_shots = []
        self.history_segments = []
        self.history_samples = []
        self.history_tests = []
        
        self.domain = domain
        self.start_node = node
        
        self.lay = QtGui.QHBoxLayout()
        self.setLayout(self.lay)
        self.legend = QtGui.QLabel()
        main = self.navigator.appwindow
        # Related docks
        self.docks = [main.measureDock, main.snapshotsDock, main.plotboardDock, 
                      main.navtoolbar, main.vtoolbar, main.breadbar, main.myMenuBar]
        self.docks_visibility = [d.isVisible() for d in self.docks]
        # Add myself to the main app space
        
        self.flashWizardDock = QtGui.QDockWidget(main.centralWidget())
        self.flashWizardDock.setWindowTitle(_('Flash Wizard'))
        self.flashWizardDock.setWidget(self)
        self.flashWizardDock.visibilityChanged.connect(self.dock_visibility_changed)
        main.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.flashWizardDock)
        # Prepare the right docking panel
        self.flashWizardPanelDock = QtGui.QDockWidget(main.centralWidget())
        self.flashWizardPanelDock.setWindowTitle(_('Flash Panel'))
        main.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.flashWizardPanelDock)
        self.flashWizardPanelDock.hide()
        
        self.activate_node(node)
        logging.debug('FlashWizard - init done', node, domain)
        
    @property
    def navigator(self):
        return self.domain.navigator
    

        
    @property
    def model_name(self):
        return self.root.flash.measure['fitting'] 
        
    def activate_node(self, node):
        self.root = node.root.get_configuration()
        self.cfg = node.get_configuration()
        p = node.path.split(':')[-1].split('/')
        logging.debug('activate_node', p)
        # Start in general mode if root, flash, measure is selected
        # or if no model was defined
        if p[-1] in (u'',u'flash',u'measure') or p[-1] in '0123456789':    
            self.page_general()
            return
        
        if not self.model_name:
            return self.page_general(highlight=True)
            
        # Start in shot selection mode if sample or segment is selected
        ntype = self.node_type(node) 
        logging.debug('activate_node type', ntype)
        if ntype=='segment':
            if check_complete_segment(self.cfg, self.model_name):
                return self.page_evaluation_segment(node)
            return self.page_select(node)
        elif ntype=='sample':
            if check_complete_sample(self.cfg, self.model_name):
                return self.page_evaluation_sample(node)
            return self.page_select(node)
        
        # Go up to shot node
        if (not node.ds) and ntype=='model':
            node = node.parent
        
        if ntype in ('shot', 'model'):
            return self.page_shot_prototype(node)
        logging.error('activate_node: failed', ntype, p, node)
        
    def node_type(self, node=False):
        node = node or self.start_node
        return node_type(node)
        
    @property
    def appwindow(self):
        return self.navigator.appwindow
        
    def showEvent(self, event):
        """Enters in the wizard-mode. Hide all non-wizard elements."""
        #self.docks_visibility = []
        for d in self.docks:
            #self.docks_visibility.append(d.isVisible())
            d.hide()
        return super(FlashWizard, self).showEvent(event)
    
    def dock_visibility_changed(self, visible=True):
        parent_visible = self.appwindow.isVisible()
        logging.debug('dock_visibility_changed', visible, parent_visible)
        if parent_visible and not visible:
            self.exit_wizard()
    
    def exit_wizard(self, *a):
        """Exits from the wizard-mode. Restore all visibility attributes."""
        logging.debug('exit_wizard')
        if sum(self.docks_visibility):
            visibility = self.docks_visibility
        else:
            visibility = self.default_dock_visibility
        
        for i, d in enumerate(self.docks):
            if visibility[i]:
                d.show()
        self.appwindow.graphWin.showMaximized()
        if self.wizard_subwindow:
            self.wizard_subwindow.hide()
            self.wizard_subwindow.deleteLater()
        self.delete_wizard_wg()
        self.flashWizardDock.hide()
        self.flashWizardDock.deleteLater()
        self.flashWizardPanelDock.hide()
        self.flashWizardPanelDock.deleteLater()
        self.deleteLater()
        
    def closeEvent(self, event):
        logging.debug('closeEvent')
        self.exit_wizard()
        return super(FlashWizard, self).closeEvent(event)
    
    wizard_subwindow = False
    wizard_wg = False
    def get_wizard_subwindow(self, wizard_wg):
        if not self.wizard_subwindow:
            self.wizard_subwindow = self.appwindow.centralWidget().addSubWindow(wizard_wg,  QtCore.Qt.WindowTitleHint)
        else:
            self.wizard_subwindow.setWidget(wizard_wg)
        self.wizard_subwindow.showMaximized()
        self.wizard_wg = wizard_wg
        
        
    def clear(self):
        while 1:
            w = self.lay.takeAt(0)
            if not w:
                break
            w = w.widget()
            if not w:
                continue
            w.hide()
            if w!=self.legend:
                w.deleteLater()
        
    def add_close(self, save=False):
        btn = QtGui.QPushButton(_('Close wizard'), parent = self)
        btn.setIcon(iutils.theme_icon('exit'))
        btn.setToolTip(_('Exit from wizard-mode'))
        btn.clicked.connect(self.parent().hide)
        if save:
            self.add_save()
        self.lay.addWidget(btn)
        self.lay.addStretch(-10)
        if self.legend.text():
            self.legend.show()
            self.lay.addWidget(self.legend)
        else:
            self.legend.hide()
            
        
    def add_save(self):
        btn = QtGui.QPushButton(_('Save'), parent = self)
        btn.setIcon(iutils.theme_icon('media-floppy'))
        btn.setToolTip(_('Save full-test results'))
        btn.clicked.connect(self.navigator.appwindow.navtoolbar.save)
        self.lay.addWidget(btn)
        
    def renode(self, node=False):
        if not node:
            self.start_node = self.renode(self.start_node)
            return self.start_node
        return self.navigator.model().tree.traverse(node.path)
    
    
    def page_general(self, highlight=False):
        self.flashWizardPanelDock.hide()
        self.get_wizard_subwindow(FlashWizardGeneral(self.root, 
                                                     self.navigator))
        if highlight:
            self.wizard_wg.global_widgets[0].label_widget.setStyleSheet(
            'QWidget { font-weight: bold; color: red; }')
        
        self.clear()
        nxt = FlashWizardPushButton(iutils.theme_icon('go-next'), 
                                 _('Select shot'), right_icon=True, parent=self)
        nxt.clicked.connect(self.page_select)
        self.lay.addWidget(nxt)
        self.legend.setText('')
        self.add_close()
        
     
    def page_select(self, node=False):
        self.flashWizardPanelDock.hide()
        node = node or self.start_node
        node = self.renode(node)
        if not self.model_name:
            self.page_general(highlight=True)
            return
        cfg = node.get_configuration()
        self.get_wizard_subwindow(FlashWizardSelectShot(cfg, 
                                                        node.linked.filename))
        
        self.clear()
        prev = FlashWizardPushButton(iutils.theme_icon('go-previous'),
                                 _('General options'), parent = self)
        prev.clicked.connect(self.page_general)
        self.lay.addWidget(prev)
        next = FlashWizardPushButton(iutils.theme_icon('go-next'),
                                 _('Modeling'), right_icon=True, parent = self)
        next.clicked.connect(self.from_select_to_shot)
        self.lay.addWidget(next)
        self.legend.setText('')
        self.add_close()
        self.flashWizardPanelDock.hide()
        
        
    def from_select_to_shot(self):
        self.renode()
        cur = self.wizard_wg.selector.current
        node = False
        if cur:
            cur = self.start_node.linked.prefix+cur[1:]
            cur = cur.strip('/')
            node = self.start_node.root.traverse(cur)
        if node:
            self.page_shot_prototype(node)
        else:
            logging.error('No shot selected', cur)
    
    def delete_wizard_wg(self):   
        if self.wizard_wg:
            self.wizard_wg.hide()
            self.wizard_wg.close()
            self.wizard_wg.deleteLater()
            self.wizard_wg = False
            return True
        return False
        
    def page_shot_prototype(self, node=False):
        # Overwrite the starting point with this node
        node = node or self.start_node
        if node.path not in self.history_shots:
            self.history_shots.append(node.path)
        node = self.renode(node)
        self.start_node = node
        self.delete_wizard_wg()
        self.wizard_wg = FlashWizardShotPrototype(node, self.navigator, self.appwindow.summaryPlot.plot)
        if self.wizard_subwindow:
            self.wizard_subwindow.hide()
        self.appwindow.graphWin.showMaximized()
        self.flashWizardPanelDock.setWidget(self.wizard_wg)
        self.flashWizardPanelDock.show()
        self.wizard_wg.show()
        # Create shot plot for node
        done = False
        section = self.wizard_wg.model_params_class.section
        section_name = self.wizard_wg.model_params_class.section_name
        for child in self.wizard_wg.cfg.devices:
            if 'model' in child and child['model'] == section_name:
                self.domain.model_plot(node.get(child['devpath']), force=True, view_model=section)
                self.wizard_wg.panel.select_results()
                done = True
                break
        if not done:
            self.domain.shot_plot(node, view_model=section)
            
        self.legend.setText(shot_legend)
        # Create buttons
        self.add_run_buttons(recursion=done)
        
        self.appwindow.vtoolbar.show()
        
    def page_evaluation(self, node=False):
        """Abstract evaluation page"""
        # Overwrite the starting point with this node
        node = self.renode(node)
        self.start_node = node
        self.delete_wizard_wg()
        self.wizard_wg = FlashWizardEvaluation(node, self.navigator, self.appwindow.summaryPlot.plot)
        if self.wizard_subwindow:
            self.wizard_subwindow.hide()
        self.appwindow.graphWin.showMaximized()
        self.flashWizardPanelDock.setWidget(self.wizard_wg)
        self.flashWizardPanelDock.show()
        self.appwindow.vtoolbar.show()
        
        return node
        
    def page_evaluation_segment(self, node=False):
        node = self.page_evaluation(node)
        self.wizard_wg.panel.select_results()
        if node.path not in self.history_segments:
            self.history_segments.append(node.path)
        
        self.legend.setText(segment_legend)
        # Create buttons
        self.add_run_buttons(recursion=True)
           
        # Create evaluation plot
        self.domain.segment_plot(node, force=True)
        return node

    def page_evaluation_sample(self, node=False):
        node = self.page_evaluation(node)
        self.wizard_wg.panel.select_results([self.wizard_wg.model_params_class.handle, 'summary'])
        if node.path not in self.history_samples:
            self.history_samples.append(node.path)
            
        self.legend.setText(sample_legend)
        # Create buttons
        self.add_run_buttons(recursion=True)
           
        # Create evaluation plot
        self.domain.sample_plot(node, force=True)
        return node
    
    def page_evaluation_test(self, node=False):
        node = self.page_evaluation(node)
        self.wizard_wg.panel.select_results(['summary'])
        if node.path not in self.history_tests:
            self.history_tests.append(node.path)
        self.legend.setText(test_legend)
        # Create buttons
        self.add_run_buttons(recursion=True)
        # Create evaluation plot
        self.domain.summary_plot(node, force=True)
        return node       
        
    def page_from_node_path(self, node_path):
        node = self.navigator.model().tree.traverse(node_path)
        # Avoid recursively checking for completeness
        if node_path in self.history_tests:
            self.page_evaluation_test(node)
        elif node_path in self.history_samples:
            self.page_evaluation_sample(node)
        elif node_path in self.history_segments:
            self.page_evaluation_segment(node)
        # Normal activation
        else:
            self.activate_node(node)
        
    def run_shot(self):
        node = self.renode()
        if self.node_type(node)=='model':
            node = node.parent
        self.domain.run_model_plugin(node, silent=True, repeat=True, 
                                     plugin=self.wizard_wg.model_plugin_class,
                                     model_plot_options={'view_model':True},
                                     callback=self.page_shot_prototype)
        
        
    def create_history_menu(self, history, all=[]):
        """Create a context menu from an history list of node paths"""
        menu = QtGui.QMenu()
        for node_path in set(history+all):
            if node_path == self.start_node.path:
                continue
            act = menu.addAction(node_path, partial(self.page_from_node_path, node_path))
            act.setCheckable(True)
            if node_path in history:
                act.setChecked(True)
        return menu
        
    def add_run_buttons(self, recursion=False):
        self.clear()
        gprev = FlashWizardPushButton(iutils.theme_icon('go-previous'),
                                 _('General options'), parent = self)
        gprev.clicked.connect(self.page_general)
        self.lay.addWidget(gprev)
        
        ntype = self.node_type(self.start_node)
        ntest = self.get_recursion_target(self.start_node, 'test')
        nsegment = False
        nsample = False
        tests = []
        samples = []
        segments = []
        shots = []
        if ntype == 'segment':
            nsegment = self.start_node
        if ntype == 'shot':
            nsegment = self.start_node.parent
        if ntype == 'model':
            nsegment = self.start_node.parent.parent
            
        if ntype=='sample':
            nsample = self.start_node
        elif nsegment:
            nsample = nsegment.parent
        
        if nsegment:
            for sh in nsegment.children.values():
                if check_complete_shot(sh.get_configuration(), self.model_name):
                    shots.append(sh.path)
        if nsample:
            for seg in nsample.children.values():
                if check_complete_segment(seg.get_configuration(), self.model_name):
                    segments.append(seg.path)
                    
        if ntest:
            for smp in ntest.children.values():
                if check_complete_sample(smp.get_configuration(), self.model_name): 
                    samples.append(smp.path)
                    
        for tst in ntest.root.children.values():
            cfg = tst.get_configuration()
            if not cfg.measure:
                continue
            if check_complete_test(cfg, self.model_name):
                tests.append(tst.path)
        
        
        prev = FlashWizardPushButton(iutils.theme_icon('go-previous'),
                                 _('Select shot'), parent = self)
        prev.clicked.connect(partial(self.page_select, self.start_node))
        menu = self.create_history_menu(self.history_shots, shots)
        if len(menu.actions()):
            prev.setMenu(menu)
        self.lay.addWidget(prev)
        
        if ntype in ('shot', 'model'):
            run_btn = FlashWizardPushButton(iutils.theme_icon('go-next'),
                                    _('Run: Shot'), right_icon=True, parent = self)
            run_btn.clicked.connect(self.run_shot)
            self.lay.addWidget(run_btn)
            
            if recursion:
                set_btn_bold(run_btn)
            
        if not recursion:
            self.add_close()
            return
        
        

        for par in [(_('Segment'), self.recurse_segment, self.history_segments, segments, 'segment'), 
                    (_('Sample'), self.recurse_sample, self.history_samples, samples, 'sample'), 
                    (_('Test'), self.recurse_test, self.history_tests, tests, 'test')]:
            run_btn = FlashWizardPushButton(iutils.theme_icon('go-next'), par[0], right_icon=True, parent = self)
            tt = _('{} recursion').format(par[0])
            run_btn.setToolTip(tt)
            run_btn.clicked.connect(par[1])
            
            set_btn_bold(run_btn, ntype == par[4])
            
            menu = self.create_history_menu(par[2], par[3])
            if len(menu.actions()):
                run_btn.setMenu(menu)
            self.lay.addWidget(run_btn)
            
        self.add_close(save=ntype=='test')
        return
    
    hierarchy = ['model', 'shot', 'segment', 'sample', 'test']
    def get_recursion_target(self, node, target):
        """Climb back to the nearest `target` node type"""
        node = self.renode(node)
        ntype = self.node_type(node)
        ni = self.hierarchy.index(ntype)
        ti = self.hierarchy.index(target)
        while ti>ni:
            if node.parent:
                node = node.parent
                ni+=1
            else:
                break
        return node
            
        
    def recurse_segment(self):
        #TODO: inherit properties from current config panel!
        self.renode()
        target_node = self.get_recursion_target(self.start_node, 'segment')
        read_conf = False
        if self.start_node!=target_node:
            read_conf = self.start_node.get_configuration()
        self.domain.run_recursive_plugin_segment(target_node, 
                                                 plugin = self.wizard_wg.model_plugin_class,
                                                 callback=partial(self.page_evaluation_segment, target_node),
                                                 read_conf = read_conf)
 
    def recurse_sample(self):
        self.renode()
        target_node = self.get_recursion_target(self.start_node, 'sample')
        read_conf = False
        if target_node!=self.start_node:
            read_conf = self.start_node.get_configuration()
        
        self.domain.run_recursive_plugin_sample(target_node, 
                                                 plugin = self.wizard_wg.model_plugin_class,
                                                 callback=partial(self.page_evaluation_sample, target_node),
                                                 read_conf = read_conf) 
 
    def recurse_test(self):
        self.renode()
        target_node = self.get_recursion_target(self.start_node, 'test')
        read_conf = False
        if target_node!=self.start_node:
            read_conf = self.start_node.get_configuration()
        
        self.domain.run_recursive_plugin_file(target_node, 
                                                 plugin = self.wizard_wg.model_plugin_class,
                                                 callback=partial(self.page_evaluation_test, target_node),
                                                 read_conf = read_conf)
        
def set_btn_bold(btn, v=True):
    """Set button `btn` as bold"""
    f = btn.font()
    f.setBold(v)
    btn.setFont(f)
        