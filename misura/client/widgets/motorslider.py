#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from aNumber import aNumber
from active import ActiveObject
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from .. import _


class MotorSlider(aNumber):

    def __init__(self, server, remObj, parent=None):
        prop = remObj.gete('goingTo')
        self.started = 0
        self.target = 0
        self.position = 0
        aNumber.__init__(self, server, remObj, prop, parent)
        self.pos_obj = ActiveObject(
            server, remObj, remObj.gete('position'), parent=self)
        self.connect(self.pos_obj, QtCore.SIGNAL('selfchanged'),
                     self.update_position, QtCore.Qt.QueuedConnection)
        if self.slider:
            self.slider.setTracking(False)
            self.slider.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.slider.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.connect(self.slider, QtCore.SIGNAL(
                'customContextMenuRequested(QPoint)'), self.showMenu)
            self.slider.wheel.connect(self.slot_slider_wheel)
        self.label_widget.setSizePolicy(QtGui.QSizePolicy.Maximum, 
                                        QtGui.QSizePolicy.Maximum)
        self.menu = QtGui.QMenu()
        self.spinact = QtGui.QWidgetAction(self.menu)
        self.spinact.setDefaultWidget(self.spinbox)
        self.labelact = QtGui.QWidgetAction(self.menu)
        self.labelact.setDefaultWidget(self.label_widget)
        self.menu.addAction(self.spinact)
        self.menu.addAction(self.labelact)
        if self.server._readLevel>=4:
            self.cfact = self.menu.addAction(_('Configure'), self.hide_show)
            self.cfact.setCheckable(True)
            if self.remObj['preset']!='factory_default':
                self.save_act = self.menu.addAction(_('Save as {}').format(self.remObj['preset']), self.save_preset)
            
        self.cf = False
        
    def slot_slider_wheel(self, e):
        print('WHEEL', e.globalX(), e.globalY(), e.delta())
        print('step', self.step, self.divider)
        print('singleStep', self.slider.singleStep(), self.slider.pageStep())
        
    
    def hide_show(self):
        """Hide/show configuration dialog"""
        from .. import conf
        if not self.cf:
            self.cf = conf.Interface(self.server, self.remObj)
        if not self.cf.isVisible():
            self.cf.show()
        else:
            self.cf.hide()
            
    def save_preset(self):
        self.remObj.set_to_preset(self.handle, 
                                   self.remObj['preset'], 
                                   self.remObj[self.handle])

    def showMenu(self, pt):
        if self.cf:
            self.cfact.setChecked(self.cf.isVisible())
        self.update()
        self.menu.popup(self.mapToGlobal(pt))

    def enterEvent(self, e):
        self.update()
        return QtGui.QWidget.enterEvent(self, e)

    def setOrientation(self, direction):
        r = aNumber.setOrientation(self, direction)
        # TODO: merge in aNumber?
        if self.slider:
            self.lay.setContentsMargins(0, 0, 0, 0)
            self.lay.setSpacing(0)
            self.slider.setContentsMargins(0, 0, 0, 0)
        return r

    def update_position(self, pos):
        self.update(position=pos)

    def update(self, *a, **k):
        if self.slider and self.slider.paused:
            return False
        s = k.pop('position', None)
        if s:
            k['minmax'] = False
        r = aNumber.update(self, *a, **k)
        if not hasattr(self, 'menu'):
            # MotorSlider not fully initialized
            return r
        # If 'position' argument was not passed,
        # force pos_obj to re-register itself
        if s is None:
            self.pos_obj.register()
            s = self.position  # keep old value
        d = abs(1. * self.current - self.started)
        if self.target != self.current:
            self.target = self.current
            self.started = s
        elif self.current == s or d == 0:
            self.started = s
            d = 0
        if d <= 5 * self.step:
            self.started = s
            s = 100
        else:
            s = 100 * (1 - abs(self.current - s) / d)
        msg = '%i%%' % abs(s)
        self.label_widget.setText(msg)
        return r


class MotorSliderAction(QtGui.QWidgetAction):

    def __init__(self, server, remObj, parent=None):
        QtGui.QWidgetAction.__init__(self, parent)
        self.wdg = MotorSlider(server, remObj, parent=parent)
        self.setDefaultWidget(self.wdg)

    def showEvent(self, event):
        self.wdg.get()
        return QtGui.QWidgetAction.showEvent(self, event)
