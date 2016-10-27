#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Show available plot pages as a storyboard."""
import tempfile
import os
import functools

from veusz import document

from misura.client.iutils import calc_plot_hierarchy

from PyQt4 import QtGui, QtCore


class Storyboard(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.base_lay = QtGui.QHBoxLayout()

        self.doc = False
        self.page = False
        self.images = {}

        self.setLayout(self.base_lay)
        self.level_modifier = 0
        self._level_modifier = 0
        self.tmpdir = tempfile.mkdtemp()
        self.cache = {}

        self.container = QtGui.QWidget()
        self.lay = QtGui.QHBoxLayout()
        self.container.setLayout(self.lay)
        self.base_lay.addWidget(self.container)

        self.controls = QtGui.QWidget(self)
        clay = QtGui.QVBoxLayout()
        self.controls.setLayout(clay)
        levelUp = QtGui.QPushButton('Up')
        levelUp.clicked.connect(self.slot_up)
        clay.addWidget(levelUp)
        levelHome = QtGui.QPushButton('Home')
        levelHome.clicked.connect(self.slot_home)
        clay.addWidget(levelHome)
        levelDown = QtGui.QPushButton('Down')
        levelDown.clicked.connect(self.slot_down)
        clay.addWidget(levelDown)
        self.controls.setMaximumWidth(75)
        self.base_lay.addWidget(self.controls)

    def slot_up(self):
        self.level_modifier -= 1
        self.update()

    def slot_down(self):
        self.level_modifier += 1
        self.update()

    def slot_home(self):
        self.level_modifier = 0
        self.update()

    def set_plot(self, plot):
        self.plot = plot
        self.doc = plot.doc
        # Connect plot sigPageChanged to set_page
        self.update_page_image()
        self.update()
        self.doc.signalModified.connect(self.update)

    def clear(self):
        while True:
            item = self.lay.itemAt(0)
            if not item:
                break
            self.lay.removeItem(item)
            w = item.widget()
            w.hide()
            self.lay.removeWidget(w)

    def fpath(self, page=False):
        if not page:
            page = self.page
        return '{}/{}.jpg'.format(self.tmpdir, page.name)

    def update_page_image(self, page=False):
        # initialize cache
        if not page:
            page = self.page
        if not page:
            return False
        if page not in self.doc.basewidget.children:
            print 'NO PAGE!'
            return False
        pageNum = self.doc.basewidget.children.index(page)
        fp = self.fpath(page)
        export = document.Export(
            self.doc,
            fp,
            pageNum,
        )

        export.export()

        # Build the label
        if page.name not in self.cache:
            lbl = QtGui.QToolButton(parent=self)
            lbl.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            func = functools.partial(self.slot_select_page, page.name)
            lbl.clicked.connect(func)
        else:
            lbl = self.cache[page.name]

        # Replace the icon
        icon = QtGui.QIcon(fp)
        lbl.setIcon(icon)
        size = QtCore.QSize(200, 100)
        pix = icon.pixmap(size)
        lbl.setIconSize(pix.size())
        self.cache[page.name] = lbl

    def update(self):
        p = self.plot.plot.getPageNumber()
        if p<len(self.doc.basewidget.children)-1:
            return False
        page = self.doc.basewidget.children[p]
        if page == self.page and self.level_modifier == self._level_modifier:
            return False
        self.clear()
        if self.page:
            self.update_page_image()
        if page == self.page:
            self._level_modifier = self.level_modifier
        else:
            self._level_modifier = 0
            self.level_modifier = 0

        self.page = page
        self.update_page_image()
        hierarchy, level, page_idx = calc_plot_hierarchy(self.doc, page)
        if level < 0:
            return False
        page_name, page_plots, crumbs = hierarchy[level][page_idx]

        N = len(hierarchy)
        level += self.level_modifier
        if level < 0:
            level = 0
        if level >= N:
            level = N - 1
        for page_name, page_plots, crumbs in hierarchy[level]:
            page = filter(
                lambda wg: wg.name == page_name, self.doc.basewidget.children)[0]
            fp = self.fpath(page)
            if not os.path.exists(fp):
                self.update_page_image(page)
            lbl = self.cache[page_name]
            lbl.setText('/'.join([''] + crumbs))
            self.lay.addWidget(lbl)
            lbl.show()

    def slot_select_page(self, page_name):
        for i, page in enumerate(self.doc.basewidget.children):
            if page.name == page_name:
                self.plot.plot.setPageNumber(i)
                break
