#!/usr/bin/python
# -*- coding: utf-8 -*-

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.plugin import navigator_domains, NavigatorDomain, node, nodes
from veusz.dialogs.plugin import PluginDialog


from .. import _
from ..filedata import getFileProxy
from ..fileui import ImageSlider
from .. import axis_selection


ism = isinstance

dilatometer_subsamples = ('Right', 'Left', 'Center','Height','Base')

class ImageAnalysisNavigatorDomain(NavigatorDomain):
    def __init__(self, *a, **k):
        super(ImageAnalysisNavigatorDomain, self).__init__(*a, **k)
        self.storyboards = {}
        self.extrusions = {}
        
    @node
    def show_storyboard(self, node):
        obj = self.storyboards.get(node.path, False)
        if obj:
            obj.show()
            return True
        obj = ImageSlider()
        obj.set_doc(self.doc)
        path = '{}/profile'.format(node.path)
        logging.debug('Storyboard path', path)
        obj.setPath(path)
        self.storyboards[node.path] = obj
        obj.show()
        
    @node
    def render(self, node=False):
        """Render video from `node`"""
        from misura.client import video
        sh = getFileProxy(node.linked.filename)
        pt = '/' + \
            node.path.replace(node.linked.prefix, '').replace('summary', '')
        v = video.VideoExporter(sh, pt)
        v.exec_()
        sh.close()
        
    @node
    def extrude(self, node=False):
        """Build profile extrusion on `node`"""
        if node.path in self.extrusions:
            self.extrusions[node.path].show()
            return True
        if not node.linked:
            logging.debug('No linked file for node', node.path)
            return False
        proxy = self.doc.proxies.get(node.linked.filename, False)
        if not proxy:
            logging.debug('No opened file for node', node.path)
            return False
        from misura.client import extrusion
        w = extrusion.extrude(proxy, node.model_path+'/profile')
        w.show()
        self.extrusions[node.path] = w
        return True
        
    @node
    def postanalysis(self, node=False):
        """Repeat image analysis on `node`"""
        if not node.linked:
            logging.debug('No linked file for node', node.path)
            return False
        proxy = self.doc.proxies.get(node.linked.filename, False)
        if not proxy:
            logging.debug('No opened file for node', node.path)
            return False
        sample = node.get_configuration()
        analyzer = sample.analyzer
        from misura.client import postanalysis
        from misura.client.live import registry 
        t = registry.tasks
        th = postanalysis.deferred_postanalysis(proxy, analyzer, sample,
                                           jobs=t.jobs,
                                           job=t.job,
                                           done=t.done)
        
    def add_sample_menu(self, menu, node):
        if node.path.split('/')[-1] in dilatometer_subsamples:
            return True
        menu.addAction(_('Open storyboard'), self.show_storyboard)
        menu.addAction(_('Render video'), self.render)
        from misura.client import extrusion, postanalysis
        if extrusion.enabled:
            menu.addAction(_('3D Extrusion'), self.extrude)
        if postanalysis.enabled:
            menu.addAction(_('Post-analysis'), self.postanalysis)
        return True
        
    def add_group_menu(self, menu, node):
        spl = node.path.split('/')
        if spl[-1] in dilatometer_subsamples:
            menu.addAction(_('Open storyboard'), self.show_storyboard)
            menu.addAction(_('Render video'), self.render)
            from misura.client import extrusion, postanalysis
            if extrusion.enabled:
                menu.addAction(_('3D Extrusion'), self.extrude)
            if postanalysis.enabled:
                menu.addAction(_('Post-analysis'), self.postanalysis)
        return True
      
class MicroscopeSampleNavigatorDomain(ImageAnalysisNavigatorDomain):
    
    
    def check_node(self, node):
        if not node:
            return False
        return 'hsm/sample' in node.path
    
    @node
    def showPoints(self, node=False):
        """Show characteristic points"""
        from misura.client import plugin
        p = plugin.ShapesPlugin(sample=node)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ShapesPlugin)
        self.mainwindow.showDialog(d)

    @node
    def hsm_report(self, node=False):
        """Execute HsmReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_hsm.vsz', 'Vol')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)   
        
    @node
    def viscosity(self, node=False):
        """Execute ViscosityPlugin on `node`"""
        from misura.client import plugin
        # Get nearest T dataset
        T=self.xnames(node, page='/temperature')[0]
        p = plugin.ViscosityPlugin(ds_in=T, ds_out=node.path+'/viscosity')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ViscosityPlugin)
        self.mainwindow.showDialog(d)

    @nodes
    def surface_tension(self, nodes):
        """Call the SurfaceTensionPlugin.
        - 1 node selected: interpret as a sample and directly use its beta,r0,Vol,T datasets
        - 2 nodes selected: interpret as 2 samples and search the node having beta,r0 children; use dil/T from the other
        - 4 nodes selected: interpret as separate beta, r0, Vol, T datasets and try to assign based on their name
        - 5 nodes selected: interpret as separate (beta, r0, T) + (dil, T) datasets and try to assign based on their name and path
        """
        if len(nodes) > 1:
            logging.debug('Not implemented')
            return False
        smp = nodes[0].children
        dbeta, nbeta = self.dsnode(smp['beta'])
        beta = nbeta.path
        dR0, nR0 = self.dsnode(smp['r0'])
        R0 = nR0.path
        ddil, ndil = self.dsnode(smp['Vol'])
        dil = ndil.path
        T = nbeta.linked.prefix + 'kiln/T'
        out = nbeta.linked.prefix + 'gamma'
        if not self.doc.data.has_key(T):
            T = ''
        # Load empty datasets
        if len(dbeta) == 0:
            self.navigator._load(nbeta)
        if len(dR0) == 0:
            self.navigator._load(nR0)
        if len(ddil) == 0:
            self.navigator._load(ndil)
        from misura.client import plugin
        cls = plugin.SurfaceTensionPlugin
        p = cls(beta=beta, R0=R0, T=T,
                dil=dil, dilT=T, ds_out=out, temperature_dataset=self.doc.data[T].data)
        d = PluginDialog(self.mainwindow, self.doc, p, cls)
        self.mainwindow.showDialog(d)
        
            
    def add_sample_menu(self, menu, node):
        j = 0
        k = ['beta', 'r0', 'Vol']
        for kj in k:
            j += node.children.has_key(kj)
        if j == len(k):
            menu.addAction(_('Surface tension'), self.surface_tension)
        menu.addAction(_('Viscosity'), self.viscosity)
        menu.addAction(_('Show Characteristic Points'), self.showPoints)
        menu.addAction(_('Report'), self.hsm_report)
        # Add generic image analysis entries
        ImageAnalysisNavigatorDomain.add_sample_menu(self, menu, node)
        return True
    
    def add_dataset_menu(self, menu, node):
        if self.is_plotted(node):
            menu.addAction(_('Show Characteristic Points'), self.showPoints)
        return True
    
class DilatometerNavigatorDomain(ImageAnalysisNavigatorDomain):
    @node
    def calibration(self, node=False):
        """Call the CalibrationFactorPlugin on the current node"""
        ds, node = self.dsnode(node)

        T = self.xnames(node, "/temperature")[0]  # in current page

        from misura.client import plugin
        p = plugin.CalibrationFactorPlugin(d=node.path, T=T)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.CalibrationFactorPlugin)
        self.mainwindow.showDialog(d)    
        
    def add_dataset_menu(self, menu, node):
        if not axis_selection.is_calibratable(node.path):
            return False
        menu.addAction(_('Calibration'), self.calibration)
        return True
    
class HorizontalSampleNavigatorDomain(DilatometerNavigatorDomain):
    
    def check_node(self, node):
        if not node:
            return False
        return 'horizontal/sample' in node.path
    
    @node
    def report(self, node=False):
        """Execute HorzizontalReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_horizontal.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)
    
    def add_sample_menu(self, menu, node): 
        menu.addAction(_('Report'), self.report)
        return True
 
class VerticalSampleNavigatorDomain(DilatometerNavigatorDomain):
    
    def check_node(self, node):
        if not node:
            return False
        return 'vertical/sample' in node.path
    
    @node
    def report(self, node=False):
        """Execute VerticalReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_vertical.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)
    
    def add_sample_menu(self, menu, node): 
        menu.addAction(_('Report'), self.report)
        return True
        
class FlexSampleNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        if not node:
            return False
        return 'flex/sample' in node.path
    @node
    def report(self, node=False):
        """Execute FlexReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_flex.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)
    
    def add_sample_menu(self, menu, node): 
        menu.addAction(_('Report'), self.report)
        return True
     
navigator_domains += [MicroscopeSampleNavigatorDomain,
            HorizontalSampleNavigatorDomain, VerticalSampleNavigatorDomain,  
            FlexSampleNavigatorDomain]
