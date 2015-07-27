#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import veusz.plugins as plugins
from PyQt4 import QtGui, QtCore

# FIXME: FieldMisuraNavigator should take dataset names!


class FieldMisuraNavigator(plugins.Field):

    """Misura Navigator to select"""

    def __init__(self, name, descr=None, depth='sample', cols=1, default=None):
        """name: name of field
        descr: description to show to user
        depth: dataset, sample, file
        """
        plugins.Field.__init__(self, name, descr=descr)
        self.depth = depth
        self.cols = cols
        self.default = default

    def makeControl(self, doc, currentwidget):
        l = QtGui.QLabel(self.descr)
        c = QtGui.QTreeView()
        otm = doc.model
        c.setModel(otm)
        c.expandAll()

        # Do the predefined selection
        obj = self.default
        if obj is None:
            return (l, c)

        jdx = otm.index_path(obj)
        n = len(jdx)
        for i, idx in enumerate(jdx):
            if i < n - 1:
                # Expand all parent objects
                c.setExpanded(idx, True)
            else:
                # Select the leaf
                c.selectionModel().setCurrentIndex(
                    jdx[-1], QtGui.QItemSelectionModel.Select)
        return (l, c)

    def getControlResults(self, cntrls):
        nav = cntrls[1]
        idx = nav.currentIndex()
        node = nav.model().data(idx, role=QtCore.Qt.UserRole)
        return node
