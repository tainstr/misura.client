#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Show available plot pages as a storyboard."""
import tempfile
import os
import functools
import textwrap

from veusz import document

from misura.client.iutils import calc_plot_hierarchy
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore
from veusz.document.operations import OperationWidgetDelete


class Storyboard(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.base_lay = QtGui.QHBoxLayout()
        self.setLayout(self.base_lay)

        self.doc = False
        self.page = False
        self.images = {}

        self.level_modifier = 0
        self._level_modifier = 0
        self.parent_modifier = False
        self._parent_modifier = False
        self.tmpdir = tempfile.mkdtemp()
        self.cache = {}

        self.container = QtGui.QWidget()
        self.lay = QtGui.QHBoxLayout()
        self.container.setLayout(self.lay)

        self.area = QtGui.QScrollArea()
        self.area.setWidget(self.container)
        self.area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.area.setWidgetResizable(True)
        self.base_lay.addWidget(self.area)

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
        self.parent_modifier = False
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
        img = page.name.replace(':', '__') + '.png'
        fp = os.path.join(self.tmpdir, img)
        return fp

    def update_page_image(self, page=False):
        # initialize cache
        if not page:
            page = self.page
        if not page:
            logging.debug('No page')
            return False
        if page not in self.doc.basewidget.children:
            logging.debug('PAGE DOES NOT EXISTS', page.name)
            return False
        pageNum = self.doc.basewidget.children.index(page)
        fp = self.fpath(page)
        logging.debug('writing page to', fp)
        export = document.Export(
            self.doc,
            fp,
            pageNum,
        )
        export.export()

        # Build the label
        if page.name not in self.cache:
            lbl = QtGui.QToolButton(parent=self.container)
            lbl.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            lbl.setStyleSheet("QToolButton { font: 12px}")
            show_func = functools.partial(self.slot_select_page, page.name)
            list_children_func = functools.partial(
                self.slot_list_children, page.name)
            del_func = functools.partial(self.slot_delete_page, page.name)
            lbl.clicked.connect(show_func)
            menu = QtGui.QMenu()
            menu.addAction('Show', show_func)
            menu.addAction('List children', list_children_func)
            menu.addAction('Delete', del_func)
            lbl.setMenu(menu)

        else:
            lbl = self.cache[page.name]

        # Replace the icon
        logging.debug('loading page from', fp)
        icon = QtGui.QIcon(fp)
        lbl.setIcon(icon)
        size = QtCore.QSize(200, 100)
        pix = icon.pixmap(size)
        lbl.setIconSize(pix.size())
        self.cache[page.name] = lbl

    def update(self, *args, **kwargs):
        force = kwargs.get('force', False)
        p = self.plot.plot.getPageNumber()
        N = len(self.doc.basewidget.children)
        #logging.debug('Storyboard.update', p, self.level_modifier, self._level_modifier)
        if p > N - 1:
            logging.debug('Cannot locate page', p, N - 1)
            p = N - 1
            # return False
        page = self.doc.basewidget.children[p]
        no_change = page == self.page and self.level_modifier == self._level_modifier and self.parent_modifier == self._parent_modifier 
        if no_change and not force:
            logging.debug('Storyboard.update: no change', page.name, self.page.name)
            return False
        if no_change and force:
            logging.debug('FORCING UPDATE!!!')
        self.clear()
        if self.page:
            self.update_page_image()
        if page == self.page:
            self._level_modifier = self.level_modifier
            self._parent_modifier = self.parent_modifier
        else:
            self._level_modifier = 0
            self.level_modifier = 0

        self.page = page
        self.update_page_image()
        hierarchy, level, page_idx = calc_plot_hierarchy(self.doc, page)
        if level < 0:
            logging.debug('Storyboard.update: negative level requested')
            return False
        page_name, page_plots, crumbs, notes = hierarchy[level][page_idx]
        N = len(hierarchy)
        level += self.level_modifier
        if level < 0:
            level = 0
        if level >= N:
            level = N - 1

        for page_name, page_plots, crumbs, notes in hierarchy[level]:
            if self.parent_modifier:
                if not page_name.startswith(self.parent_modifier):
                    continue
            page = filter(
                lambda wg: wg.name == page_name, self.doc.basewidget.children)[0]
            fp = self.fpath(page)
            if not os.path.exists(fp):
                self.update_page_image(page)
            lbl = self.cache[page_name]
            txt = '/'.join([''] + crumbs)
            if notes:
                notes = textwrap.fill(notes, 25, break_long_words=False)
                txt+='\n'+notes
            lbl.setText(txt)
            self.lay.addWidget(lbl)
            lbl.show()

    def slot_list_children(self, page_name):
        self.parent_modifier = page_name
        self.slot_down()

    def slot_select_page(self, page_name):
        p = -1
        for i, page in enumerate(self.doc.basewidget.children):
            if page.name == page_name:
                self.plot.plot.setPageNumber(i)
                p = 1
                break
        if p < 0:
            logging.debug('Selected page was not found! Update...', page_name)
            self.update(force=True)
        return p

    def slot_delete_page(self, page_name):
        p = -1
        for i, page in enumerate(self.doc.basewidget.children):
            if page.name == page_name:
                logging.debug('Deleting page', page_name, i, page)
                op = OperationWidgetDelete(page)
                self.doc.applyOperation(op)
                p = i
                break
        self.update(force=True)
