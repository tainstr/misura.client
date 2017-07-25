#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from PyQt4 import QtCore, QtGui
from traceback import format_exc
from misura.client.parameters import MAX, MIN, MAXINT, MININT
from misura.client.widgets.active import ActiveWidget, extend_decimals
import math
from misura.canon.logger import get_module_logging
from misura.canon import option
import numpy as np
logging = get_module_logging(__name__)

from traceback import print_exc


class FocusableSlider(QtGui.QSlider):
    zoom = QtCore.pyqtSignal(bool)
    pause = QtCore.pyqtSignal(bool)

    def __init__(self, *a, **kw):
        QtGui.QSlider.__init__(self, *a, **kw)
        self.paused = False
        self.zoomed = False

    def set_paused(self, v):
        """Change paused state for the slider."""
        if self.paused == v:
            return False
        self.paused = v
        self.pause.emit(v)
        return True

    def mousePressEvent(self, ev):
        self.set_paused(True)
        return QtGui.QSlider.mousePressEvent(self, ev)

    def mouseReleaseEvent(self, ev):
        self.set_paused(False)
        return QtGui.QSlider.mouseReleaseEvent(self, ev)

    def mouseDoubleClickEvent(self, ev):
        self.set_paused(False)
        self.zoomed = 1 ^ self.zoomed
        self.zoom.emit(self.zoomed)
        return QtGui.QSlider.mouseDoubleClickEvent(self, ev)


class ScientificSpinbox(QtGui.QDoubleSpinBox):
    scientific_decimals = 8
    double = True
    flexibleChanged = QtCore.pyqtSignal(object)
    float_decimals = 0
    precision = -1
    def __init__(self, double=True, scientific_decimals=8, parent=None):
        QtGui.QDoubleSpinBox.__init__(self, parent=parent)
        self.scientific_decimals = scientific_decimals
        self.set_double(double)
        self.valueChanged.connect(self.reemit)
        
    def set_double(self, val):
        self.double = val
        if not self.double:
            self.setDecimals(0)
        else:
            self.setDecimals(1000)
            self.float_decimals = 2      
        
    def update_float_decimals(self):
        p = self.precision if self.precision >= 0 else 2
        dc = extend_decimals(self.value(), p)
        self.float_decimals = dc 
        
    def set_precision(self, p):
        self.precision=p
        self.update_float_decimals()
        self.setValue(self.value())
             
    def reemit(self, value):
        if not self.double:
            value = int(value)
        self.flexibleChanged.emit(value)      

    def textFromValue(self, value):
        self.update_float_decimals()
        l = 0
        if value != 0:
            l = abs(math.log(abs(value), 10))
        pre = False
        if l > self.scientific_decimals:
            pre = '{:.' + str(self.scientific_decimals) + 'e}'
        elif self.double:
            pre = '{:.' + str(self.float_decimals) + 'f}'
        if pre:
            text = pre.format(value).replace('.', self.locale().decimalPoint())
        else:
            text = str(int(value))
        return text

    def valueFromText(self, text):
        if not self.double:
            return int(text)
        text = text.replace(self.locale().groupSeparator(), 
                            self.locale().decimalPoint())
        ok = True
        try:
            v = float(text.replace(self.locale().decimalPoint(), '.'))
        except:
            print_exc()
            ok = False
        if not ok:
            v, ok = self.locale().toFloat(text)
        if not ok:
            v = 0
        return v

    def validate(self, text, pos):
        if text in ('', '-', '+'):
            return (QtGui.QValidator.Intermediate, text, pos)
        if not self.double:
            try:
                int(text)
                return (QtGui.QValidator.Acceptable, text, pos)
            except:
                return (QtGui.QValidator.Invalid, text, pos)
        v, ok = self.locale().toFloat(text)
        if not ok:
            try:
                v = float(text)
                ok = True
            except:
                pass
        if not ok:
            t = text.lower().replace(self.locale().decimalPoint(), '.')
            if t.endswith('e') or t.endswith('e-') or t.endswith('e+'):
                ok = True
                return (QtGui.QValidator.Intermediate, text, pos)
        if not ok:
            return (QtGui.QValidator.Invalid, text, pos)
        return (QtGui.QValidator.Acceptable, text, pos)

class SpinboxAction(QtGui.QWidgetAction):
    def __init__(self, label, current=0, minimum=None, maximum=None, step=1, 
                 double=True, callback=lambda *a: 0, parent=None):
        QtGui.QWidgetAction.__init__(self, parent)
        if minimum is None:
            minimum = MIN if double else MININT
        if maximum is None:
            maximum = MAX if double else MAXINT
        self.label = QtGui.QLabel(label)
        self.spinbox = ScientificSpinbox(double=double)
        self.spinbox.setRange(minimum, maximum)
        self.spinbox.setValue(current)
        self.spinbox.set_precision(4)
        self.spinbox.setSingleStep(step)
        self.spinbox.editingFinished.connect(callback)
        
        self.w = QtGui.QWidget()
        lay = QtGui.QVBoxLayout()
        lay.addWidget(self.label)
        lay.addWidget(self.spinbox)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.w.setLayout(lay)
        self.setDefaultWidget(self.w)
        

class aNumber(ActiveWidget):
    zoom_factor = 1.
    zoomed = False
    precision = -1
    error = None
    slider_class = FocusableSlider
    spinbox = False
    slider = False
    
    def __init__(self, server, remObj, prop, parent=None, slider_class=FocusableSlider):
        self.slider_class = slider_class
        ActiveWidget.__init__(self, server, remObj, prop, parent)
        
        
    def changed_option(self):
        self.precision = self.prop.get('precision', -1)
        self.divider = 1.
        # Initializing
        if not self.spinbox:
            return 
        min_value = self.prop.get('min', None)
        max_value = self.prop.get('max', None)
        step = self.prop.get('step', False)
        if self.type == 'Float' or type(0.1) in [type(self.current), 
                                                 type(min_value),
                                                 type(max_value),
                                                 type(step)]:
            self.double = True
        else:
            self.double = False
        self.spinbox.set_double(self.double)
        self.setRange(min_value, max_value, step)
        # Connect signals
        if self.readonly:
            if self.slider:
                self.slider.setEnabled(False)
            self.spinbox.setReadOnly(True)
        else:
            if self.slider:
                self.connect(
                    self.slider, QtCore.SIGNAL('valueChanged(int)'), self.sliderPush)
            self.spinbox.flexibleChanged.connect(self.boxPush)
        self.update(minmax=False)
        self.spinbox.set_precision(self.precision)
        self.build_range_menu()
        
    def redraw(self):
        # Create the layout
        super(aNumber, self).redraw()
        # If max/min are defined, create the slider widget
        if None not in [self.prop.get('min', None), self.prop.get('max', None)]:
            self.slider = self.slider_class(QtCore.Qt.Horizontal, parent=self)
            self.slider.zoom.connect(self.setZoom)
            self.lay.addWidget(self.slider)
            
        self.spinbox = ScientificSpinbox(parent=self)
        self.spinbox.setKeyboardTracking(False)
        self.lay.addWidget(self.spinbox)
        
        self.changed_option()
        

        
    def build_range_menu(self):
        #TODO: update ranges when unit changes!!!
        self.range_menu = self.emenu.addMenu(_('Range'))
        mx = self.max or 0
        mn  = self.min or 0
        st = self.step or 0
        logging.debug('Build range menu', self.handle, mx, mn,st,self.precision, self.zoom_factor)
        self.range_min = SpinboxAction(_('Min'), mn, maximum=mx or None, 
                                       callback=self.set_range_minimum, parent=self)
        self.range_menu.addAction(self.range_min)
        self.range_max = SpinboxAction(_('Max'), mx, minimum=mn or None, 
                                       callback=self.set_range_maximum, parent=self)
        self.range_menu.addAction(self.range_max)
        self.range_step = SpinboxAction(_('Step'), st, minimum=0, maximum=(mx-mn)/3., 
                                       callback=self.set_range_step, parent=self)
        self.range_menu.addAction(self.range_step)
        self.range_zoom = SpinboxAction(_('Zoom'), self.zoom_factor, minimum=1., maximum=1e8, 
                                       callback=self.set_zoom_factor, parent=self)
        self.range_menu.addAction(self.range_zoom)
        self.range_precision = SpinboxAction(_('Precision'), self.precision, minimum=-1, maximum=12, step=1,
                                             double=False, callback=self.set_precision, parent=self)
        self.range_menu.addAction(self.range_precision)
        return True
        
                
    def set_range_minimum(self):
        val = self.range_min.spinbox.value()
        self.prop['min'] = val
        self.min = val
        self.setRange(self.min, self.max, self.step)
        
    def set_range_maximum(self):
        val = self.range_max.spinbox.value()
        self.prop['max'] = val
        self.max = val
        self.setRange(self.min, self.max, self.step)
        
    def set_range_step(self):
        val = self.range_step.spinbox.value()
        self.prop['step'] = val
        self.step = val
        self.setRange(self.min, self.max, self.step)
        
        
    def set_zoom_factor(self):
        if not self.slider:
            return
        self.zoom_factor = self.range_zoom.spinbox.value()
        self.slider.zoomed = self.zoom_factor>1
        self.setZoom()
        
    def set_precision(self):
        self.precision = self.range_precision.spinbox.value()
        self.spinbox.set_precision(self.precision)
        self.set_tooltip()

    def set_error(self, error=None):
        if error is None:
            err = self.prop.get('error', None)
            if err and self.remObj.has_key(err):
                error = self.remObj.get(err)
        self.error = error
        if error is None:
            self.spinbox.setSuffix('')
            return False
        template = u'{}'
        if self.double:
            p = self.precision if self.precision > 0 else 1
            dc = extend_decimals(error, p)
            template = u'{:.' + str(dc) + u'f}'.replace('.', self.locale().decimalPoint())
        self.spinbox.setSuffix(u' \u00b1 ' + template.format(error))
        return True

    def setOrientation(self, direction):
        if not self.slider:
            return
        sp = [QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed]
        if direction == QtCore.Qt.Horizontal:
            lay = QtGui.QHBoxLayout()
            self.slider.setOrientation(QtCore.Qt.Horizontal)
            self.setSizePolicy(*sp)
            self.slider.setSizePolicy(*sp)
        else:
            self.slider.setOrientation(QtCore.Qt.Vertical)
            self.setSizePolicy(*sp[::-1])
            self.slider.setSizePolicy(*sp[::-1])
            lay = QtGui.QVBoxLayout()
        # Reposition all items on the new layout
        while True:
            i = self.lay.takeAt(0)
            if i <= 0:
                break
            lay.addWidget(i.widget())
        QtGui.QWidget().setLayout(self.layout())
        self.setLayout(lay)
        self.lay = lay

    def boxPush(self, target=None):
        if target == None:
            target = self.spinbox.value()
        if self.double:
            target = float(target)
        else:
            target = int(target)
        # Remove focus from spinbox, so everything can be updated
        if self.spinbox.hasFocus():
            if self.slider:
                self.slider.setFocus()
            elif self.parent():
                self.parent().setFocus()

        if self.set(target) != target:
            self.update()

    def sliderPush(self, target=None):
        if target == None:
            target = self.slider.value()
        target = target / self.divider
        if self.double:
            target = float(target)
        else:
            target = int(target)
        if self.slider:
            self.slider.set_paused(False)

        if self.set(target) != target:
            self.update()

    def setZoom(self, val=None):
        """Enable/disable zooming"""
        if self.slider:
            if self.slider.zoomed:
                self.slider.setStyleSheet("background-color: red;")
                if self.zoom_factor==1:
                    self.zoom_factor = 10.
            else:
                self.slider.setStyleSheet("background-color:;")
                if self.zoom_factor!=1:
                    self.zoom_factor = 1.
        self.range_zoom.spinbox.setValue(self.zoom_factor)
        self.setRange(self.min, self.max, self.step)

    def update(self, minmax=True):
        self.set_tooltip()
        if self.slider and self.slider.paused:
            return False
        # Block remote updates while editing
        if self.spinbox.hasFocus():
            logging.debug('aNumber.update has focus - skipping')
            return False
        self.set_error()
        self.spinbox.blockSignals(True)
        # Update minimum and maximum
        if self.slider and minmax:
            # FIXME: These two lines causes incredible slowdown!
            # self.prop=self.remObj.gete(self.handle)
            # self.current=self.prop['current']
            if not self.slider or not self.slider.zoomed:
                self.setRange(self.prop.get('min', None),
                          self.prop.get('max', None),
                          self.prop.get('step', False))
            self.slider.blockSignals(True)
        # Translate server-side value into client-side units
        cur = self.adapt2gui(self.current)
        try:
            if not self.double:
                cur = int(cur)
            if not self.slider or not self.slider.zoomed:
                self.setRange(self.min, self.max, self.step)
            #print 'aNumber.update',self.handle,cur,self.current
            self.spinbox.setValue(cur)
            if self.slider:
                self.slider.setValue(int(cur * self.divider))
        except:
            logging.debug(format_exc())
        finally:
            self.spinbox.blockSignals(False)
            if self.slider:
                self.slider.blockSignals(False)

    def setRange(self, m=None, M=None, step=0):
        #TODO: All this part might be moved into ScientificSpinbox
        step = self.adapt2gui(step)
        cur = self.adapt2gui(self.current)
        self.max, self.min = None, None
        if m != None and M != None and m!=M:
            m = self.adapt2gui(m)
            M = self.adapt2gui(M)
            self.min, self.max = m, M
        else:
            if M == None:
                if self.double:
                    M = MAX
                else:
                    M = MAXINT
            else:
                self.max = M
            if m == None:
                if self.double:
                    m = MIN
                else:
                    m = MININT
            else:
                self.min = m
        if self.slider and self.slider.zoomed:
            d = abs(M - m) / self.zoom_factor
            m = max((cur - d, m))
            M = min((cur + d, M))
        if self.double:
            m = float(m)
            M = float(M)
        else:
            m = int(m)
            M = int(M)
        self.spinbox.setRange(m, M)
        self.step = step
        if step==0:
            step=abs(M-m)/100.
        step /= self.zoom_factor
        if not self.double:
            step=int(step)
            if step==0:
                step=1
        self.spinbox.setSingleStep(step)
        
        if self.slider:
            self.divider = 10.**(-abs(np.log10(step)))
            logging.debug('Slider:', m, M, step, self.divider)
            self.slider.blockSignals(True)
            #print 'aNumber.setRange slider',m,M,step,cur, self.divider
            self.slider.setRange(int(m * self.divider), int(M * self.divider))
            self.slider.setSingleStep(int(step * self.divider))
            self.slider.setPageStep(int(step * 5 * self.divider))
            self.slider.setValue(cur*self.divider)
            self.slider.blockSignals(False)
        self.set_tooltip()
            
    def set_tooltip(self):
        mx, mn = 'inf', '-inf'
        if self.max and ((self.double and self.max<MAX) or (self.max<MAXINT)):
            mx = self.spinbox.textFromValue(self.max)
        if self.min and ((self.double and self.min>MIN) or (self.min>MININT)):
            mn = self.spinbox.textFromValue(self.min)
        tp = _('Range: {} >> {}\nStep: {}\n').format(mn, mx, self.step)
        tp += _('Precision: {}').format(self.precision)
        if self.slider:
            tp += _(' Zoom: {}').format(self.zoom_factor*self.slider.zoomed)
        err = self.prop.get('error', None)
        if err:
            tp += _('Error: {}').format(err)
        if self.slider:
            self.slider.setToolTip(tp)
        self.spinbox.setToolTip(tp)

class aNumberAction(QtGui.QWidgetAction):

    def __init__(self, server, remObj, prop, parent=None):
        QtGui.QWidgetAction.__init__(self, parent)
        self.w = QtGui.QWidget()
        self.lay = QtGui.QVBoxLayout()
        self.w.setLayout(self.lay)
        self.wdg = aNumber(server, remObj, prop, parent=parent)
        self.lay.addWidget(self.wdg.label_widget)
        self.lay.addWidget(self.wdg)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.setDefaultWidget(self.w)

    def showEvent(self, event):
        self.wdg.get()
        return QtGui.QWidgetAction.showEvent(self, event)
    

