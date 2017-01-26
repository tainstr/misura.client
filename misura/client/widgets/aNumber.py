#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from PyQt4 import QtCore, QtGui
from traceback import format_exc
from misura.client.parameters import MAX, MIN
from misura.client.widgets.active import ActiveWidget, extend_decimals
import math
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)


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
        logging.debug('mousePressEvent')
        self.set_paused(True)
        return QtGui.QSlider.mousePressEvent(self, ev)

    def mouseReleaseEvent(self, ev):
        logging.debug('mouseReleaseEvent')
        self.set_paused(False)
        return QtGui.QSlider.mouseReleaseEvent(self, ev)

    def mouseDoubleClickEvent(self, ev):
        self.zoomed = 1 ^ self.zoomed
        self.zoom.emit(self.zoomed)
        logging.debug('mouseDoubleClickEvent', self.zoomed)
        return QtGui.QSlider.mouseDoubleClickEvent(self, ev)


class aNumber(ActiveWidget):
    zoom_factor = 10.
    zoomed = False
    precision = -1
    error = None

    def __init__(self, server, remObj, prop, parent=None, slider_class=FocusableSlider):
        ActiveWidget.__init__(self, server, remObj, prop, parent)
        min_value = self.prop.get('min', None)
        max_value = self.prop.get('max', None)
        step = self.prop.get('step', False)

        self.precision = self.prop.get('precision', -1)
        self.divider = 1.
        # If max/min are defined, create the slider widget
        self.slider = False
        if None not in [max_value, min_value]:
            self.slider = slider_class(QtCore.Qt.Horizontal, parent=self)
            self.slider.zoom.connect(self.setZoom)
            self.lay.addWidget(self.slider)
        # Identify float type from type or current/max/min/step
        if self.type == 'Float' or type(0.1) in [type(self.current), type(min_value), type(max_value), type(step)]:
            self.double = True
            self.sValueChanged = 'valueChanged(double)'
            self.spinbox = QtGui.QDoubleSpinBox(parent=self)
        else:
            self.double = False
            self.sValueChanged = 'valueChanged(int)'
            self.spinbox = QtGui.QSpinBox(parent=self)
        self.spinbox.setKeyboardTracking(False)
        self.lay.addWidget(self.spinbox)
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
#               self.connect(self.slider, QtCore.SIGNAL('pause(bool)'), self.update)
            self.connect(
                self.spinbox, QtCore.SIGNAL(self.sValueChanged), self.boxPush)
        self.update(minmax=False)

    def set_error(self, error=None):
        if error is None:
            error = self.prop.get('error', None)
            if error and self.remObj.has_key(error):
                error = self.remObj.get(error)
        self.error = error
        if error is None:
            self.spinbox.setSuffix('')
            return False
        template = u'{}'
        if self.double:
            p = self.precision if self.precision > 0 else 1    
            dc = extend_decimals(error, default=0, extend_by=p)    
            template = u'{:.' + str(dc) + u'f}'
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

    def setZoom(self, val):
        """Enable/disable zooming"""
        self.setRange(self.min, self.max, self.step)
        if self.slider:
            if self.slider.zoomed:
                self.slider.setStyleSheet("background-color: red;")
            else:
                self.slider.setStyleSheet("background-color:;")

    def update(self, minmax=True):
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
            self.slider.blockSignals(True)
            # FIXME: These two lines causes incredible slowdown!
            # self.prop=self.remObj.gete(self.handle)
            # self.current=self.prop['current']
            self.setRange(self.prop.get('min', None),
                          self.prop.get('max', None),
                          self.prop.get('step', False))
        # Translate server-side value into client-side units
        cur = self.adapt2gui(self.current)
        try:
            if self.double:
                p = self.precision if self.precision > 0 else 1    
                dc = extend_decimals(cur, default=0, extend_by=p)
                self.spinbox.setDecimals(dc)
            else:
                cur = int(cur)
            self.setRange(self.min, self.max, self.step)
# print 'aNumber.update',
# self.handle,cur,self.current,self.spinbox.maximum(),self.spinbox.minimum()
            self.spinbox.setValue(cur)
#           self.setRange(self.min, self.max, self.step)
            if self.slider:
                self.slider.setValue(int(cur * self.divider))
        except:
            logging.debug(format_exc())
        finally:
            self.spinbox.blockSignals(False)
            if self.slider:
                self.slider.blockSignals(False)

    def setRange(self, m=None, M=None, step=0):
        step = self.adapt2gui(step)
        cur = self.adapt2gui(self.current)
        self.max, self.min = None, None
        if m != None and M != None:
            m = self.adapt2gui(m)
            M = self.adapt2gui(M)
            if not step:
                step = abs(M - m) / 100.
            if self.double:
                m = float(m)
                M = float(M)
            else:
                m = int(m)
                M = int(M)
                step = int(step)
                if step == 0:
                    step = 1
            self.min, self.max = m, M
        else:
            if M == None:
                if self.double:
                    M = MAX
                else:
                    M = 2147483647
            else:
                self.max = M
            if m == None:
                if self.double:
                    m = MIN
                else:
                    m = -2147483647
            else:
                self.min = m
            step = cur / 10.
        if self.slider and self.slider.zoomed:
            d = abs(M - m) / self.zoom_factor
            m = max((cur - d, m))
            M = min((cur + d, M))
            step = step / d
#       print 'Setting range',m,M,step
        if self.double:
            self.divider = 10.**self.spinbox.decimals()
        else:
            step = int(step)
            m = int(m)
            M = int(M)
        if step == 0:
            step = 1
        self.spinbox.setRange(m, M)
        self.step = step
        self.divider = 1
        self.spinbox.setSingleStep(step * self.divider)
#       print 'aNumber.setRange',self.handle,min,max,step,cur
        if self.slider:
            self.slider.setMaximum(M * self.divider)
            self.slider.setMinimum(m * self.divider)
            self.slider.setSingleStep(step * self.divider)
            self.slider.setPageStep(step * 2 * self.divider)


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
