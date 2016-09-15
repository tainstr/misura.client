#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Breadcrumb plot pages navigator."""
import collections
from functools import partial

from misura.client.iutils import calc_plot_hierarchy, most_involved_node

from PyQt4 import QtGui, QtCore


class Crumb(QtGui.QLabel):
    """Clickable label allowing to navigate through siblings of a breadcrumb level"""
    sigSelectPage = QtCore.pyqtSignal(str)
    menu = False

    def __init__(self, name, doc, hierarchy, parent=None):
        name = name.split('/')
        while name[0] == '':
            name.pop(0)
        self.name = name
        self.label = self.name[-1]
        self.doc = doc
        self.hierarchy = hierarchy
        QtGui.QLabel.__init__(self, self.label, parent=parent)
        self.menu = QtGui.QMenu(self)
        self.build_menu()

    def build_menu(self):
        """Builds menu for upward navigation"""
        self.menu.clear()
        self.callables = []
        for page, page_plots, crumbs in self.hierarchy:
            # if crumbs == self.name:
            #    continue
            func = partial(self.sigSelectPage.emit, page)
            self.callables.append(func)
            self.menu.addAction('/'.join([''] + crumbs), func)

    def show_menu(self, event):
        """Show associated menu"""
        self.menu.popup(event.globalPos())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.show_menu(event)
        return QtGui.QLabel.mousePressEvent(self, event)


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
        page = self.doc.basewidget.children[p]
        hierarchy = calc_plot_hierarchy(self.doc)
        inpage = False
        for level, pages in enumerate(hierarchy):
            for page_name, page_plots, crumbs in pages:
                if page_name == page.name:
                    inpage = True
                    break
            if inpage:
                break
        if not inpage:
            return False

        self.crumbs = []
        # Create crumb widgets
        name = ''
        for i, label in enumerate(crumbs):
            name += '/' + label
            self.add_crumb(name, hierarchy[i])

        if level >= len(hierarchy) - 1:
            return

        next = []
        for h in hierarchy[level + 1:]:
            next += h
        if next:
            self.add_crumb('>>', next)

    def add_crumb(self, name, hierarchy_level):
        crumb = Crumb(name, self.doc, hierarchy_level)
        self.lay.addWidget(crumb)
        crumb.sigSelectPage.connect(self.slot_select_page)
        self.crumbs.append(crumb)
        return crumb

    def slot_select_page(self, page_name):
        for i, page in enumerate(self.doc.basewidget.children):
            if page.name == page_name:
                self.plot.plot.setPageNumber(i)
                break
