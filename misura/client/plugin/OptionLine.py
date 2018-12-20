#!/usr/bin/python
# -*- coding: utf-8 -*-
from traceback import format_exc
from misura.canon.logger import get_module_logging
from django.contrib.gis.gdal.raster import const
logging = get_module_logging(__name__)
import veusz.setting as setting
import veusz.document as document
from veusz import widgets
from .OptionAbstractWidget import OptionAbstractWidget
from . import utils
from misura.client import _

class OptionLine(utils.OperationWrapper, OptionAbstractWidget, widgets.Line):
    typename = 'optionline'
    description = "Line for xy plots, linked to options for intercept and slope"

    def __init__(self, *args, **kwargs):
        widgets.Line.__init__(self, *args, **kwargs)
        if type(self) == OptionLine:
            self.readDefaults()
        self.opt_name = []
        self.connected = False
        self.addAction(widgets.widget.Action('up', self.update,
                                                   descr='Update Line',
                                                   usertext='Update Line'))
        self.addAction(widgets.widget.Action('apply', self.update,
                                                   descr='Apply',
                                                   usertext='Apply line position to configuration'))
        for name in ('invert', 'intercept', 'slope','dataset'):
            self.settings.get(name).setOnModified(self.update)

    @classmethod
    def allowedParentTypes(klass):
        """Get types of widgets this can be a child of."""
        return (widgets.PointPlotter,)
    
    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        widgets.Line.addSettings(s)
        ##########
        # Add specific settings
        s.add( setting.Dataset(
            'dataset', '',
            descr=_('Dataset pointing to the containing options'),
            usertext=_('Dataset')), 0 ) 
        
        s.add(setting.Str('intercept', '',
                          descr='Intercept option path',
                          usertext='Intercept option path'),
              1)
        s.add(setting.Str('slope', '',
                          descr='Slope option path',
                          usertext='Slope option path'),
              1)
        s.add(setting.Float('scale', 1.,
                          descr='Scale values by factor',
                          usertext='Scale'),
              1)
        s.add(setting.Bool('invert', False,
                          descr='Invert coordinates (y->x)',
                          usertext='Invert coordinates',
                          formatting=True),
              1)
        
        
        #############
        # Modify/hide existing settings
        mode = s.get('mode')
        mode.default = 'point-to-point'
        mode.set('point-to-point')
        mode.hidden = True
        
        #s.get('xPos').hidden = True
        #s.get('yPos').hidden = True
        #s.get('xPos2').hidden = True
        #s.get('yPos2').hidden = True
        s.get('xAxis').hidden = True
        s.get('yAxis').hidden = True
        s.get('length').hidden = True
        s.get('angle').hidden = True
        
        clip = s.get('clip')
        clip.default = True
        clip.hidden = True
        clip.set(True)
        
        pos = s.get('positioning')
        pos.default = 'axes'
        pos.set('axes')
        pos.hidden = True
        

        
    def get_proxies_and_options(self, conf):
        # Allow intercept to be defined by a + operation
        opts = list(self.settings.intercept.split('+'))
        opts += list(self.settings.slope.split('+'))
        for opt in opts:
            proxy, name= conf.from_column(opt)
            yield proxy, name
            
    def calc_intercept(self):
        const = 0
        for i in xrange(self.settings.intercept.count('+')+1):
            const += self.proxy[i][self.opt_name[i]]
        return const*self.settings.scale
    
    def calc_slope(self):
        ic = self.settings.intercept.count('+')+1
        sc = self.settings.slope.count('+')+1
        slope = 0
        for i in xrange(ic, ic+sc):
            if not self.opt_name[i]:
                break
            slope += self.proxy[i][self.opt_name[i]]
        return slope*self.settings.scale
        
    def update(self):
        OptionAbstractWidget.update(self)
        curve = self.parent
        graph = curve.parent
        # Curve axis - original
        xAxis = graph.getChild(curve.settings.xAxis)
        yAxis = graph.getChild(curve.settings.yAxis)
        if not self.proxy or not xAxis or not yAxis:
            logging.debug('Incomplete settings - not updating')
            return 
        try:
            const = self.calc_intercept()
            slope = self.calc_slope()
        except:
            logging.error(self.proxy,self.opt_name)
            logging.error(format_exc())
            return False
        if self.settings.invert:
            ymin, ymax = yAxis.getPlottedRange()
            xmin, xmax = const+slope*ymin, const+slope*ymax
        else:
            xmin, xmax = xAxis.getPlottedRange()
            ymin, ymax = const+slope*xmin, const+slope*xmax
            
        self.settings.xAxis = curve.settings.xAxis
        self.settings.yAxis = curve.settings.yAxis
        self.settings.xPos = xmin
        self.settings.yPos = ymin
        self.settings.xPos2 = xmax
        self.settings.yPos2 = ymax
        self.doc.setModified(True)
        
        
    def push_update(self):
        """Send current line settings to the Misura configuration"""
        pass
    
    def draw(self, posn, phelper, outerbounds = None):
        self.check_update()
        self.parent.getAxes = self.getAxes
        widgets.Line.draw(self, posn, phelper, outerbounds)

        for c in self.children:
            c.draw(posn, phelper, outerbounds)
            
        
    def getAxes(self, *args, **kwargs):
        """Needed to allow children drawing"""
        graph_ancestor = utils.searchFirstOccurrence(self, "graph", -1)
        return graph_ancestor.getAxes(*args, **kwargs)
        

        

document.thefactory.register(OptionLine)
