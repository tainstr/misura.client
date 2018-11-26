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
from misura.client import _
from ..iutils import theme_icon
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
        levelUp = QtGui.QPushButton()
        levelUp.setIcon(theme_icon('go-up'))
        levelUp.clicked.connect(self.slot_up)
        clay.addWidget(levelUp)
        levelHome = QtGui.QPushButton()
        levelHome.setIcon(theme_icon('go-home'))
        levelHome.clicked.connect(self.slot_home)
        clay.addWidget(levelHome)
        levelDown = QtGui.QPushButton()
        levelDown.setIcon(theme_icon('go-down'))
        levelDown.clicked.connect(self.slot_down)
        clay.addWidget(levelDown)
        self.levelFilter = QtGui.QLabel(self.container)
        self.levelFilter.setMinimumWidth(300)
        #clay.addWidget(self.levelFilter)
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
        self.levelFilter.setText('')
        self.levelFilter.setToolTip('')
        self.update()

    def set_plot(self, plot):
        logging.debug('set_plot', plot)
        self.plot = plot
        self.doc = plot.doc
        # Connect plot sigPageChanged to set_page
        self.update_page_image()
        self.update()
        self.doc.model.sigPageChanged.connect(self.update)

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
        
        if page.name in self.cache:
            lbl, changeset = self.cache[page.name]
            if changeset>=self.doc.changeset:
                logging.debug('Not updating page', changeset, self.doc.changeset)
                return False
        if page.name in self.doc.cached_pages:
            logging.debug('Not updating cached page', page.name)
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
            lbl.setCheckable(True)
            show_func = functools.partial(self.slot_select_page, page.name)
            lbl.clicked.connect(show_func)
            menu = QtGui.QMenu()
            menu.aboutToShow.connect(functools.partial(self.build_page_menu, menu, page, pageNum))
            lbl.setMenu(menu)

        else:
            lbl, changeset = self.cache[page.name]

        # Replace the icon
        logging.debug('loading page from', fp)
        icon = QtGui.QIcon(fp)
        lbl.setIcon(icon)
        size = QtCore.QSize(200, 100)
        pix = icon.pixmap(size)
        lbl.setIconSize(pix.size())
        self.cache[page.name] = lbl, self.doc.changeset
        return True
    
    def build_page_menu(self, menu, page, pageNum):
        menu.clear()
        list_children_func = functools.partial(
            self.slot_list_children, page.name)
        del_func = functools.partial(self.slot_delete_page, page.name)
        export_func = functools.partial(self.slot_export_page, pageNum)
        del_children_func = functools.partial(self.slot_delete_children, page)
        show_func = functools.partial(self.slot_select_page, page.name)
        menu.addAction(_('Show'), show_func)
        menu.addAction(_('List children'), list_children_func)
        menu.addAction(_('Delete'), del_func)
        menu.addAction(_('Delete recursively'), del_children_func)
        menu.addAction(_('Export'), export_func)
        if page.name not in self.doc.cached_pages:
            cache_func = functools.partial(self.slot_cache_page, page.name)
            menu.addAction(_('Cache page'), cache_func)
        else:
            retrieve_func = functools.partial(self.slot_retrieve_page, page.name)
            menu.addAction(_('Retrieve from cache'), retrieve_func)
    
    def slot_cache_page(self, path):
        self.doc.cache_page(path)
        
    def slot_retrieve_page(self, path):
        self.doc.retrieve_page(path)
    
    def highlight(self):
        for k in self.cache:
            lbl = self.cache[k][0]
            lbl.setChecked(k==self.page.name)
            
            
    def iter_page_level(self, page, level_modifier=0):
        hierarchy, level, page_idx = calc_plot_hierarchy(self.doc, page)
        if level < 0:
            logging.debug('Storyboard.iter_page_level: negative level requested')
            return []
        page_name, page_plots, crumbs, notes = hierarchy[level][page_idx]
        N = len(hierarchy)
        level += level_modifier
        if level < 0:
            level = 0
        if level >= N:
            level = N - 1

        return hierarchy[level]
            
            
    def update(self, *args, **kwargs):
        force = kwargs.get('force', False)
        p = self.plot.plot.getPageNumber()
        N = len(self.doc.basewidget.children)
        if p > N - 1:
            logging.debug('Cannot locate page', p, N - 1)
            p = N - 1
            # return False
        page = self.doc.basewidget.children[p]
        no_change = page == self.page and self.level_modifier == self._level_modifier and self.parent_modifier == self._parent_modifier
        if no_change and not force:
            logging.debug('Storyboard.update: no change',
                          page.name, self.page.name)
            self.highlight()
            return False
        if no_change and force:
            logging.debug('FORCING UPDATE!!!')
        self.clear()
        oldpage = False
        if self.page:
            oldpage = self.page
            self.update_page_image()
        if page == self.page:
            self._level_modifier = self.level_modifier
            self._parent_modifier = self.parent_modifier
        else:
            self._level_modifier = 0
            self.level_modifier = 0

        self.page = page
        if self.page != oldpage:
            self.update_page_image()
            
        for page_name, page_plots, crumbs, notes in self.iter_page_level(page, self.level_modifier):
            if self.parent_modifier:
                if not page_name.startswith(self.parent_modifier):
                    continue
            page = filter(
                lambda wg: wg.name == page_name, self.doc.basewidget.children)[0]
            fp = self.fpath(page)
            if not os.path.exists(fp):
                logging.debug('Non existing page icon', page_name, fp)
                self.update_page_image(page)
            lbl = self.cache[page_name][0]
            txt = '/'.join([''] + crumbs)
            if notes:
                notes = textwrap.fill(notes, 25, break_long_words=False)
                txt += '\n' + notes
            lbl.setText(txt)
            self.lay.addWidget(lbl)
            lbl.show()
            
        self.highlight()

    def slot_list_children(self, page_name):
        if page_name.lower().endswith('_t'):
            page_name = page_name[:-2]
        self.parent_modifier = page_name
        self.levelFilter.setText(self.parent_modifier)
        self.levelFilter.setToolTip(self.parent_modifier)
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
        else:
            if page==self.page:
                self.highlight()
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
        
    def slot_delete_children(self, page):
        parent_modifier = page.name
        if parent_modifier.lower().endswith('_t'):
            parent_modifier = parent_modifier[:-2]
        ops = []
        for page_name, page_plots, crumbs, notes in self.iter_page_level(page, +1):
            if not page_name.startswith(parent_modifier):
                continue
            if page_name == page.name:
                continue
            cpage = filter(lambda wg: wg.name == page_name, 
                          self.doc.basewidget.children)[0]
            self.slot_delete_children(cpage)
            logging.debug('Deleting page', page_name, cpage)
            ops.append(OperationWidgetDelete(cpage))
        op = document.OperationMultiple(ops, "DeletePageChildren")
        self.doc.applyOperation(op)
        
    def slot_export_page(self, page_num):
        self.plot.plot.slotPageExport(page_num=page_num)
