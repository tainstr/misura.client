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
        self.lay = QtGui.QHBoxLayout()

        self.doc = False
        self.page = False
        self.images = {}
        
        self.setLayout(self.lay)
        
        self.tmpdir = tempfile.mkdtemp()
        self.cache = {}
        
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
        return '{}/{}.jpg'.format(self.tmpdir,page.name)
    
    def update_page_image(self, page=False, crumbs=['']):
        # initialize cache
        if not page:
            page = self.page
        if not page:
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
            lbl.setText('/'.join(['']+crumbs))
            lbl.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            func = functools.partial(self.slot_select_page, page.name)        
            lbl.clicked.connect(func)
        else:
            lbl = self.cache[page.name]
        
        # Replace the icon    
        icon = QtGui.QIcon(fp)
        lbl.setIcon(icon)
        size = QtCore.QSize(200,100)
        pix = icon.pixmap(size)
        lbl.setIconSize(pix.size())
        
        self.cache[page.name] = lbl
        
    def update(self):
        p = self.plot.plot.getPageNumber()
        page = self.doc.basewidget.children[p]
        if page == self.page:
            return False
        self.clear()
        if self.page:
            self.update_page_image()
        self.page = page
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
        
        for page_name, page_plots, crumbs in hierarchy[level]:
            page = filter(lambda wg: wg.name==page_name, self.doc.basewidget.children)[0]
            fp = self.fpath(page)
            if not os.path.exists(fp):
                self.update_page_image(page, crumbs)
            lbl = self.cache[page_name]
            self.lay.addWidget(lbl)
            lbl.show()
            
    def slot_select_page(self, page_name):
        for i, page in enumerate(self.doc.basewidget.children):
            if page.name == page_name:
                self.plot.plot.setPageNumber(i)
                break