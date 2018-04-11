#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from PyQt4 import QtCore, QtGui
from traceback import format_exc
from misura.client.parameters import MAX, MIN, MAXINT, MININT
from misura.client.widgets.active import ActiveWidget, extend_decimals
import math

from misura.canon.csutil import lockme
import numpy as np

from misura.canon.logger import get_module_logging

logging = get_module_logging(__name__)

from traceback import print_exc
from ..iutils import theme_icon


class FocusableSlider(QtGui.QSlider):
    zoom = QtCore.pyqtSignal(bool)
    pause = QtCore.pyqtSignal(bool)
    wheel = QtCore.pyqtSignal(QtGui.QWheelEvent)
    zoom_factor = 1.

    def __init__(self, *a, **kw):
        QtGui.QSlider.__init__(self, *a, **kw)
        self.paused = False

    @property
    def zoomed(self):
        return self.zoom_factor != 1.

    @zoomed.setter
    def zoomed(self, val):
        if not val:
            self.zoom_factor = 1.
        else:
            self.zoom_factor = 10.

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

    def wheelEvent(self, e):
        self.wheel.emit(e)
        return super(FocusableSlider, self).wheelEvent(e)

    def plus(self, n=0):
        n = n or int(self.singleStep() / self.zoom_factor)
        print('PLUS', n, self.singleStep())
        self.setValue(self.value() + n)
        self.valueChanged.emit(self.value())

    def minus(self, n=0):
        n = n or self.singleStep()
        self.plus(-n)


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
        self.precision = p
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
        self.label.setForegroundRole(QtGui.QPalette.BrightText)
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


def ir(a): return int(round(a, 0))


class aNumber(ActiveWidget):
    zoom_factor = 1.
    zoomed = False
    precision = -1
    error = None
    slider_class = FocusableSlider
    spinbox = False
    slider = False
    range_menu = False
    step_changed = QtCore.pyqtSignal(float)
    arrow_plus = False
    arrow_minus = False

    def __init__(self, server, remObj, prop, parent=None, slider_class=FocusableSlider):
        self.slider_class = slider_class
        ActiveWidget.__init__(self, server, remObj, prop, parent)
        self.arrow_act = QtGui.QAction(_('Arrows'), self)
        self.arrow_act.setCheckable(True)
        self.arrow_act.setChecked(False)
        self.arrow_act.triggered.connect(self.toggle_arrows)
        self.invert_act = QtGui.QAction(_('Inverted'), self)
        self.invert_act.setCheckable(True)
        self.invert_act.setChecked(False)
        self.invert_act.triggered.connect(self.toggle_invert)
        self.zoomact = QtGui.QAction(_('Zoom'), self)
        self.zoomact.setCheckable(True)
        self.zoomact.setChecked(False)
        self.zoomact.triggered.connect(self.toggle_zoom)
        
        

    def changed_option(self):
        self.precision = self.prop.get('precision', -1)
        self.divider = 1.
        self.current = self.prop.get('current')
        # Initializing
        if not self.spinbox:
            self.update(minmax=False)
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
                self.slider.hide()
            self.spinbox.setReadOnly(True)
            self.spinbox.hide()
            self.readonly_label.show()
        else:
            if self.slider:
                self.connect(
                    self.slider, QtCore.SIGNAL('valueChanged(int)'), self.sliderPush)
            self.spinbox.flexibleChanged.connect(self.boxPush)
            self.readonly_label.hide()
            self.spinbox.show()
            if self.slider:
                self.slider.show()
        self.spinbox.set_precision(self.precision)
        self.update(minmax=False)
        self.build_range_menu()
        self.set_enabled()

    def redraw(self):
        # Create the layout
        super(aNumber, self).redraw()
        # If max/min are defined, create the slider widget
        if None not in [self.prop.get('min', None), self.prop.get('max', None)]:
            self.slider = self.slider_class(QtCore.Qt.Horizontal, parent=self)
            self.slider.zoom.connect(self.setZoom)

            self.arrow_plus = QtGui.QPushButton()
            self.arrow_plus.clicked.connect(self.slider.plus)

            self.arrow_minus = QtGui.QPushButton()
            self.arrow_minus.clicked.connect(self.slider.minus)

            for btn in (self.arrow_plus, self.arrow_minus):
                btn.setFlat(True)
                btn.setSizePolicy(QtGui.QSizePolicy.Minimum,
                                  QtGui.QSizePolicy.Minimum)
                btn.setMinimumSize(10, 10)
                btn.setMaximumSize(25, 25)
                btn.setAutoRepeat(True)
                btn.hide()
                
            self.set_arrows_icons()

            self.lay.insertWidget(self.lay.count() - 2, self.arrow_minus)
            self.lay.insertWidget(self.lay.count() - 2, self.slider)
            self.lay.insertWidget(self.lay.count() - 2, self.arrow_plus)

        self.spinbox = ScientificSpinbox(parent=self)
        self.spinbox.setKeyboardTracking(False)
        self.lay.insertWidget(self.lay.count() - 2, self.spinbox)
        self.changed_option()

    def toggle_arrows(self, show=None):
        if show is None:
            show = self.arrow_act.isChecked()
        logging.debug('Add/remove arrows', show)
        self.arrow_act.setChecked(show)
        if show:
            self.arrow_plus.show()
            self.arrow_minus.show()
        else:
            self.arrow_plus.hide()
            self.arrow_minus.hide()
    
    def toggle_zoom(self):
        if self.zoom_factor == 1.:
            self.zoom_factor = 10.
        else:
            self.zoom_factor = 1.
        if self.slider:
            self.slider.zoom_factor = self.zoom_factor
        self.setZoom()
        logging.debug('Toggle zoom2', self.zoom_factor)

    def build_range_menu(self):
        # TODO: update ranges when unit changes!!!
        if not self.range_menu:
            self.range_menu = self.emenu.addMenu(_('Range'))
            self.range_menu.aboutToShow.connect(self.update_range_menu)
        else:
            self.range_menu.clear()
        mx = self.max or 0
        mn = self.min or 0
        st = self.step or 0
        self.range_min = SpinboxAction(_('Min'), mn, maximum=mx or None,
                                       callback=self.set_range_minimum, parent=self)
        self.range_menu.addAction(self.range_min)
        self.range_max = SpinboxAction(_('Max'), mx, minimum=mn or None,
                                       callback=self.set_range_maximum, parent=self)
        self.range_menu.addAction(self.range_max)
        stm = max(((mx - mn) / 3., st))
        self.range_step = SpinboxAction(_('Step'), st, minimum=0, maximum=stm,
                                        callback=self.set_range_step, parent=self)
        self.range_menu.addAction(self.range_step)
        self.range_zoom = SpinboxAction(_('Zoom'), self.zoom_factor, minimum=1., maximum=1e8,
                                        callback=self.set_zoom_factor, parent=self)
        self.range_menu.addAction(self.range_zoom)
        self.range_precision = SpinboxAction(_('Precision'), self.precision, minimum=-1, maximum=12, step=1,
                                             double=False, callback=self.set_precision, parent=self)
        self.range_menu.addAction(self.range_precision)
        return True

    def update_range_menu(self):
        self.range_min.spinbox.setValue(self.min or 0)
        self.range_max.spinbox.setValue(self.max or 0)
        self.range_step.spinbox.setValue(self.step or 0)
        self.range_zoom.spinbox.setValue(self.zoom_factor)
        self.range_precision.spinbox.setValue(self.precision or 0)

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
        self.setZoom()

    def set_precision(self):
        self.precision = self.range_precision.spinbox.value()
        self.spinbox.set_precision(self.precision)
        self.set_tooltip()
        self.update()

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
            template = u'{:.' + str(dc) + u'f}'.replace('.',
                                                        self.locale().decimalPoint())
        self.spinbox.setSuffix(u' \u00b1 ' + template.format(error))
        return True

    def set_inverted_arrows(self, invert=False):
        if not self.slider:
            logging.debug('Cannot set inverted arrows: no slider!')
            return False
        pi = self.lay.indexOf(self.arrow_plus)
        mi = self.lay.indexOf(self.arrow_minus)
        orient = self.slider.orientation() 
        straight = (orient == QtCore.Qt.Horizontal and pi > mi) or (orient == QtCore.Qt.Vertical and pi < mi)
        #logging.debug('set_inverted_arrows:', mi, pi, invert, self.slider.orientation(), straight)
        if straight!=invert:
            logging.debug('set_inverted_arrows: nothing to do')
            return
        #logging.debug('do set_inverted_arrows', pi, mi, type(invert), type(straight))
        self.lay.removeWidget(self.arrow_plus)
        self.lay.removeWidget(self.arrow_minus)
        wgs = [(self.arrow_plus, mi), (self.arrow_minus, pi)]
        if mi > pi:
            wgs = wgs[::-1]
        for wg, i in wgs:
            self.lay.insertWidget(i, wg)
            if orient == QtCore.Qt.Vertical:
                wg.setContentsMargins(25, 25, 25, 25)
            else:
                wg.setContentsMargins(0, 0, 0, 0)
        self.set_arrows_icons()

    def set_inverted_slider(self, val=False):
        if not self.slider:
            logging.debug('Cannot set inverted slider: no slider!')
            return False
        logging.debug('set_inverted_slider', val)
        self.slider.setInvertedControls(val)
        self.slider.setInvertedAppearance(val)
        self.set_inverted_arrows(val)
        return True

    def toggle_invert(self):
        val = self.slider.invertedControls()^1
        self.set_inverted_slider(val)

    def set_arrows_icons(self):
        icons = ['go-next', 'go-previous']
        wg = [self.arrow_plus, self.arrow_minus]
        if self.slider.orientation() == QtCore.Qt.Vertical:
            icons = ['go-up', 'go-down']
        if self.slider.invertedControls():
            icons=icons[::-1]
        for i, w in enumerate(wg):
            w.setIcon(theme_icon(icons[i]))

    def setOrientation(self, direction):
        if not self.slider:
            return
        sp = [QtGui.QSizePolicy.MinimumExpanding,
              QtGui.QSizePolicy.Maximum]
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
        self.set_arrows_icons()
        self.set_inverted_slider()

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
            logging.debug('setZoom', self.slider.zoom_factor, self.zoom_factor, self.slider.zoomed)
            self.zoom_factor = self.slider.zoom_factor
            if self.slider.zoomed:
                self.slider.setStyleSheet("background-color: red;")
            else:
                self.slider.setStyleSheet("background-color:;")
            self.zoomact.setChecked(self.slider.zoomed)
            
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
            if not self.slider.zoomed:
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
            # print 'aNumber.update',self.handle,cur,self.current
            self.spinbox.setValue(cur)
            if self.slider:
                self.slider.setValue(ir(cur * self.divider))
        except:
            logging.debug(format_exc())
        finally:
            self.spinbox.blockSignals(False)
            if self.slider:
                self.slider.blockSignals(False)
        c = int(self.current)
        if c in self.prop.get('valueSignals', {}):
            self.readonly_label.setText(str(self.prop['valueSignals'][c]))
        else:
            self.readonly_label.setText(self.spinbox.text())

    #@lockme()
    def setRange(self, m=None, M=None, step=0):
        # TODO: All this part might be moved into ScientificSpinbox
        step = self.adapt2gui(step)
        cur = self.adapt2gui(self.current)
        self.max, self.min = None, None
        if m != None and M != None and m != M:
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

        self.step = step
        if step == 0:
            if (M - m) < MAXINT / 2:
                step = abs(M - m) / 100.
            else:
                step = 1
        step /= self.zoom_factor
        if not self.double:
            step = int(step)
            if step == 0:
                step = 1

        self.spinbox.setRange(m, M)
        self.spinbox.setSingleStep(step)

        if self.slider and step:
            self.divider = 10.**(-np.log10(step))
            s = self.slider.signalsBlocked()
            self.slider.blockSignals(True)

            #print('aNumber.setRange slider',self.prop['kid'], m,M,step,cur, self.divider)

            self.slider.setRange(ir(m * self.divider), ir(M * self.divider))
            self.slider.setSingleStep(ir(step * self.divider))
            self.slider.setPageStep(ir(step * 5 * self.divider))
            self.slider.setValue(ir(cur * self.divider))

            # print('aNumber slider', self.prop['kid'], self.slider.singleStep(), self.slider.pageStep(), self.slider.value(),
            #      self.slider.minimum(), self.slider.maximum() )

            self.slider.blockSignals(s)

        #print('aNumber spinbox', self.prop['kid'], self.spinbox.singleStep(), self.spinbox.minimum(), self.spinbox.maximum())
        self.set_tooltip()
        self.step_changed.emit(self.step)

    def set_tooltip(self):
        mx, mn = 'inf', '-inf'
        if self.max and ((self.double and self.max < MAX) or (self.max < MAXINT)):
            mx = self.spinbox.textFromValue(self.max)
        if self.min and ((self.double and self.min > MIN) or (self.min > MININT)):
            mn = self.spinbox.textFromValue(self.min)
        tp = _('Range: {} >> {}\nStep: {}\n').format(mn, mx, self.step)
        tp += _('Precision: {}').format(self.precision)
        if self.slider:
            tp += _(' Zoom: {}').format(self.zoom_factor * self.slider.zoomed)
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
