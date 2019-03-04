#!/usr/bin/python
# -*- coding: utf-8 -*-
from traceback import format_exc
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.setting as setting
import veusz.document as document
from veusz.document.operations import OperationWidgetAdd
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
        self.addAction(widgets.widget.Action('apply', self.apply,
                                                   descr='Apply',
                                                   usertext='Apply line position to configuration'))
        self.line_label = False
        #for name in ('invert', 'intercept', 'slope'):
        #    self.settings.get(name).setOnModified(self.update)
        self.settings.get('legend').setOnModified(self.set_legend)

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
        s.add(setting.Str('legend', '',
                          descr='Legend',
                          usertext='Legend'),
              1)
        s.add(setting.Str('intercept', '',
                          descr='Intercept option path',
                          usertext='Intercept option path'),
              1)
        s.add(setting.Bool('intercept_ro', False,
                          descr='Forbid changing intercapt on plot',
                          usertext='Set intercept read-only'),
              2)
        s.add(setting.Str('slope', '',
                          descr='Slope option path',
                          usertext='Slope option path'),
              3)
        s.add(setting.Bool('slope_ro', True,
                          descr='Forbid changing slope on plot',
                          usertext='Set slope read-only'),
              4)
        s.add(setting.Str('updaters', '',
                          descr='Options forcing an update when changed',
                          usertext='Updater options'),
              5)
        s.add(setting.Float('scale', 1.,
                          descr='Scale values by factor',
                          usertext='Scale'),
              6)
        
        
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
        
        s.get('xPos').hidden = True
        s.get('yPos').hidden = True
        s.get('xPos2').hidden = True
        s.get('yPos2').hidden = True
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
        opts += list(self.settings.updaters.split(';'))
        for opt in opts:
            proxy, name= conf.from_column(opt)
            yield proxy, name
            
    def get_intercept(self):
        const = 0
        for i in xrange(self.settings.intercept.count('+')+1):
            const += self.proxy[i][self.opt_name[i]]
        return const*self.settings.scale
    
    def get_slope(self):
        ic = self.settings.intercept.count('+')+1
        sc = self.settings.slope.count('+')+1
        slope = 0
        for i in xrange(ic, ic+sc):
            if not self.opt_name[i]:
                break
            slope += self.proxy[i][self.opt_name[i]]
        return slope*self.settings.scale
    
    def set_intercept(self, val):
        """In case of summation, only the first will be taken"""
        if self.settings.intercept_ro:
            return
        ic = self.settings.intercept.count('+')+1
        # Subtract any subsequent addendum
        for i in xrange(1,ic):
            val -= self.proxy[i][self.opt_name[i]]
        self.proxy[0][self.opt_name[0]] = val/self.settings.scale
        from misura.client.live import registry
        kid = self.proxy[0].getattr(self.opt_name[0], 'kid')
        registry.force_redraw([kid])
        
    def set_slope(self, val):
        """In case of summation, only the first will be taken"""
        if self.settings.slope_ro:
            return
        ic = self.settings.intercept.count('+')+1
        self.proxy[ic][self.opt_name[ic]] = val/self.settings.scale
        from misura.client.live import registry
        kid = self.proxy[ic].getattr(self.opt_name[ic], 'kid')
        registry.force_redraw([kid])
        
        
    def update(self):
        curve = self.parent
        if not self.settings.dataset:
            logging.debug('Resetting dataset to parent', curve.settings.yData)
            self.settings.dataset = curve.settings.yData
        OptionAbstractWidget.update(self)
        graph = curve.parent
        # Curve axis - original
        xAxis = graph.getChild(curve.settings.xAxis)
        yAxis = graph.getChild(curve.settings.yAxis)
        if not self.proxy or not xAxis or not yAxis:
            logging.debug('Incomplete settings - not updating', self.path, self.proxy, xAxis, yAxis)
            return False
        try:
            const = self.get_intercept()
            slope = self.get_slope()
        except:
            logging.error('Cannot update option line', self.path)
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
        self.set_legend()
        logging.debug('end update', self.path, self.opt_name)
        return True
    
    def set_legend(self):
        legend = self.settings.legend
        if not self.line_label:
            logging.debug('Creating child LineLabel...')
            op = OperationWidgetAdd(self, 'linelabel', name='legend')
            self.document.applyOperation(op)
            self.line_label = self.getChild('legend')
        self.line_label.settings.label = legend
        self.line_label.settings.hide = not bool(legend)
        self.line_label.settings.angle = -90.*self.settings.invert
        self.line_label.update()
        
        
    def updateControlItem(self, *a, **k):
        r = super(OptionLine, self).updateControlItem(*a, **k)
        self.apply()
        self.update()
        return r
        
        
    def apply(self):
        """Send current line settings to the Misura configuration"""
        x1, y1 = self.settings.xPos[0], self.settings.yPos[0]
        x2, y2 = self.settings.xPos2[0], self.settings.yPos2[0]
        if self.settings.invert:
            ys = x1, x2
            x1, x2 = y1, y2
            y1, y2 = ys
        dx = x2-x1
        slope = self.get_slope()
        const = self.get_intercept()
        if abs(dx)>0:
            if not self.settings.slope_ro:
                slope = (y2-y1)/(x2-x1)
            if not self.settings.intercept_ro:
                const = y2-slope*x2 
        else:
            slope = 0.
            const = y1 
        self.set_slope(slope)
        self.set_intercept(const)
        
        
    
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

