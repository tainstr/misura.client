#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Breadcrumb plot pages navigator."""
import collections

from misura.client.iutils import calc_plot_hierarchy

from PyQt4 import QtGui, QtCore
from ccm.Pages import Page


class Crumb(QtGui.QLabel):
    """Clickable label allowing to navigate through siblings of a breadcrumb level"""
    sigSelectPage = QtCore.pyqtSignal(str)
    def __init__(self, level, label='', parent=None):
        self.label = label
        self.level = level
        QtGui.QLabel.__init__('/'+label, parent=parent)
        

class Breadcrumb(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.lay = QtGui.QHBoxLayout()

        self.doc = False
        self.page = False

        self.setLayout(self.lay)

    def set_plot(self, plot):
        self.plot = plot
        self.doc = plot.doc
        # Connect plot sigPageChanged to set_page
        self.update()
        self.doc.signalModified.connect(self.update)

    def set_page(self, page):
        self.page = page
        self.update()

    def clear(self):
        while True:
            item = self.lay.itemAt(0)
            if not item:
                break
            self.lay.removeItem(item)
            w = item.widget()
            w.hide()
            self.lay.removeWidget(w)

    def update(self):
        self.clear()
        p = self.plot.plot.getPageNumber()
        pwg = self.doc.basewidget.children[p]
        page = '/' + pwg.name
        hierarchy = calc_plot_hierarchy(self.doc.model.plots['plot'])
        for plots in hierarchy:
            inpage = filter(lambda p: p.startswith(page), plots)
            if inpage:
                break
        if not inpage:
            print 'EMPTY BREADCRUMB'
            return False
        # Collect all involved datasets
        involved = []
        for inp in inpage:
            involved += self.doc.model.plots['plot'][inp]
        # Find the common ancestor
        involved = [inv.split('/') for inv in involved]
        lengths = [len(inv) for inv in involved]
        max_len = max(lengths)
        best_count = 0
        crumbs = []
        for i in range(min(lengths)):
            # Exclude the last element
            if len(crumbs)>=max_len-1:
                break
            level = [inv[i] for inv in involved]
            data = collections.Counter(level)
            best = data.most_common(1)[0][0]
            count = level.count(best) 
            # Stop if the count decreases
            if count<best_count:
                break
            best_count = count
            crumbs.append(best)
        # Create crumb widgets
        for level, name in enumerate(crumbs):
            crumb = Crumb(level, name)
            self.lay.addWidget(crumb)
