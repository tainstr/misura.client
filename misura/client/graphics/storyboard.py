#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Show available plot pages as a storyboard."""
import tempfile
import os
import functools
import textwrap

from veusz import document
from veusz.utils import pixmapAsHtml
from misura.client.iutils import calc_plot_hierarchy
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.client import _
from ..iutils import theme_icon
from PyQt4 import QtGui, QtCore
from veusz.document.operations import OperationWidgetDelete

class PlotPreviewLabel(QtGui.QToolButton):
    
    def mousePressEvent(self, event):
        if event.button()==QtCore.Qt.RightButton:
            self.showMenu()
            event.accept()
            return 
        return QtGui.QToolButton.mousePressEvent(self, event)
    

class Storyboard(QtGui.QWidget):
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.base_lay = QtGui.QHBoxLayout()
        self.setLayout(self.base_lay)
        self.multiselection = []
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
        
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.slot_delete_selected_pages()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_E:
            self.slot_export_page()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self.highlight()
            event.accept()
            return
        return QtGui.QWidget.keyPressEvent(self, event)

    def slot_up(self):
        self.level_modifier -= 1
        return self.update()

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
            lbl = PlotPreviewLabel(parent=self.container)
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
        tooltip = "<html>{}</html>".format(pixmapAsHtml(icon.pixmap(QtCore.QSize(1000, 500))))
        lbl.setToolTip(tooltip)
        lbl.setStyleSheet("QToolTip { color: #0000; background-color: #ffff; border: none; }")
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
        menu.addAction(_('Delete')+ ' - (Del)', del_func)
        menu.addAction(_('Delete recursively'), del_children_func)
        menu.addAction(_('Export'+ ' - (E)'), export_func)
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
        self.multiselection = []
            
            
    def iter_page_level(self, page, level_modifier=0):
        hierarchy, level, page_idx = calc_plot_hierarchy(self.doc, page)
        if level < 0:
            logging.debug('Storyboard.iter_page_level: negative level requested')
            return []
        page_name, page_plots, crumbs, notes = hierarchy[level][page_idx]
        N = len(hierarchy)
        maxmod = N-level-1
        minmod = -level
        level += level_modifier
        if level < 0:
            level = 0
        if level >= N:
            level = N - 1
        
        return hierarchy[level], minmod, maxmod
            
            
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
            
        selected_hierarchy, minmod, maxmod = self.iter_page_level(page, self.level_modifier)
        for (page_name, page_plots, crumbs, notes) in selected_hierarchy:
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
        self.limit_level_modifier(minmod, maxmod)
        self.highlight()
        
    def limit_level_modifier(self, minmod, maxmod):
        if self._level_modifier > maxmod:
            self.level_modifier = maxmod
            self._level_modifier = maxmod
        elif self._level_modifier < minmod:
            self.level_modifier = minmod
            self._level_modifier = minmod

    def slot_list_children(self, page_name):
        if page_name.lower().endswith('_t'):
            page_name = page_name[:-2]
        self.parent_modifier = page_name
        self.levelFilter.setText(self.parent_modifier)
        self.levelFilter.setToolTip(self.parent_modifier)
        self.slot_down()
        
    @property
    def multiselect(self):
        return QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier
    
    def highlight_multiselection(self):
        for k, (lbl, cs) in self.cache.items():
            lbl.setChecked(k in self.multiselection)
 
    def slot_select_page(self, page_name):
        p = -1
        for i, page in enumerate(self.doc.basewidget.children):
            if page.name == page_name:
                p = 1
                if self.multiselect:
                    self.multiselection.append(page_name)
                    self.highlight_multiselection()
                    break
                self.plot.plot.setPageNumber(i)
                break
        if p < 0:
            logging.debug('Selected page was not found! Update...', page_name)
            self.update(force=True)
        elif not self.multiselect:
            if page==self.page:
                self.highlight()
        return p

    def slot_delete_page(self, page_name, force=False):
        """Delete selected `page_name`"""
        p = -1
        for i, page in enumerate(self.doc.basewidget.children):
            if page.name == page_name:
                logging.debug('Deleting page', page_name, i, page)
                op = OperationWidgetDelete(page)
                self.doc.applyOperation(op)
                p = i
                break
        self.update(force=True)
        
    def slot_delete_selected_pages(self):
        for page_name in self.multiselection:
            logging.debug('slot_delete_selected_pages', page_name)
            self.slot_delete_page(page_name, force=True)
        self.highlight()
        
    def slot_delete_children(self, page):
        """Recursively delete all child pages starting from selected `page`"""
        parent_modifier = page.name
        if parent_modifier.lower().endswith('_t'):
            parent_modifier = parent_modifier[:-2]
        ops = []
        selected_hierarchy, minmod, maxmod = self.iter_page_level(page, +1)
        for page_name, page_plots, crumbs, notes in selected_hierarchy:
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
        
    def slot_export_page(self, page_num=None):
        # Export all selected pages
        if page_num is None:
            selected = list(self.multiselection)
            page_num = []
            for i, page in enumerate(self.doc.basewidget.children):
                if page.name in selected:
                    page_num.append(i)
            
        self.plot.plot.slotPageExport(page_num=page_num)
        self.highlight()
