#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Date and Time widget"""
from time import time
from active import *
from .. import _


class aTime(ActiveWidget):

    """Date and time widget"""
    delta = 0
    """Local time - remote time delta."""

    def __init__(self, server, path,  prop, parent=None):
        ActiveWidget.__init__(self, server, path,  prop, parent)
        
    def redraw(self):
        super(aTime, self).redraw()
        self.twg = QtGui.QDateTimeEdit(parent=self)
        self.lay.addWidget(self.twg)
        # Cause immediate update after complete init
        self.emit(QtCore.SIGNAL('selfchanged()'))
        self.twg.setReadOnly(self.readonly)
        if not self.readonly:
            # TODO: add calendar widget if not editing.
            self.connect(
                self.twg,  QtCore.SIGNAL('dateTimeChanged(QDateTime)'), self.edited)
        if hasattr(self.server, 'time'):
            t = time()
            s = self.server.time()
            dt = time() - t
            self.delta = (t - s) + (dt / 3.)

    def adapt2gui(self, val):
        return ActiveWidget.adapt2gui(self, val + self.delta) * 1000

    def adapt2srv(self, val):
        return ActiveWidget.adapt2srv(self, val - self.delta)

    def update(self):
        self.twg.blockSignals(True)
        dt = QtCore.QDateTime()
        dt.setMSecsSinceEpoch(self.adapt2gui(self.current))
        self.twg.setDateTime(dt)
        self.twg.blockSignals(False)
        self.set_enabled()

    def edited(self, qdt=None):
        if qdt is None:
            qdt = self.twg.dateTime()
        t = qdt.toMSecsSinceEpoch() / 1000.
        self.set(t)


class aDelay(aTime):

    """A specialized aTime widget for server delayed start management."""

    def __init__(self, *a, **k):
        aTime.__init__(self, *a, **k)
        self.is_delay_enabled()

    def get(self, *a, **k):
        """Propagate edits when delayStart is disabled, so remote value can be read again."""
        if self.is_delay_enabled():
            self.current = self.twg.dateTime().toMSecsSinceEpoch() / 1000.
        aTime.get(self, *a, **k)

    def enterEvent(self, event):
        """Mouse enter event should fire only if delayStart is disabled."""
        if self.is_delay_enabled():
            return
        return aTime.enterEvent(self, event)

    def focusInEvent(self, event):
        self.is_delay_enabled()
        return aTime.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.is_delay_enabled()
        return aTime.focusOutEvent(self, event)

    def is_delay_enabled(self):
        en = self.remObj['delayStart']
        if en:
            self.twg.setReadOnly(True)
        else:
            self.twg.setReadOnly(False)
        return en
