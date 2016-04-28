#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import veusz.plugins as plugins
from PyQt4 import QtGui
from ..conf import Interface

class FieldConfigurationProxy(plugins.Field):

    """Misura Navigator to select"""

    def __init__(self, name, descr=None, default=None):
        """name: name of field
        descr: description to show to user
        """
        plugins.Field.__init__(self, name, descr=descr)
        self.proxy = default

    def makeControl(self, doc, currentwidget):
        label = QtGui.QLabel(self.descr)
        control = Interface(self.proxy)
        return (label, control)

    def getControlResults(self, cntrls):
        return self.proxy

plugins.FieldConfigurationProxy = FieldConfigurationProxy