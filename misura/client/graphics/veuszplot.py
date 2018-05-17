#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple plotting for browser and live acquisition."""
import os
from functools import partial
from base64 import b64encode

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from veusz import qtall as qt4
from PyQt4 import QtGui, QtCore


from .. import filedata, plugin
from .. import _
from ..iutils import searchFirstOccurrence

MAX = 10**5
MIN = -10**5
import veusz.setting.settingdb as setdb
import veusz.windows.treeeditwindow as treeeditwindow
import veusz.document as document
from veusz.dialogs import dataeditdialog
from veusz.document import registerImportCommand

import veusz.windows.plotwindow as plotwindow
import veusz.setting as setting
from veusz.document import OperationWidgetDelete




def _(text, disambiguation=None, context='PlotWindow'):
    """Translate text."""
    return qt4.QCoreApplication.translate(context, text, disambiguation)


def with_busy_cursor(function_to_decorate):
    def wrapper(*a, **k):
        qt4.QApplication.setOverrideCursor(qt4.QCursor(qt4.Qt.WaitCursor))

        try:
            function_to_decorate(*a, **k)
        finally:
            qt4.QApplication.restoreOverrideCursor()

    return wrapper

def process_image_dragMoveEvent(event):
        logging.debug('dragMoveEvent', event.mimeData())
        if event.mimeData().hasFormat("image/png"):
            event.acceptProposedAction()  
            
def process_image_dropEvent(plot_window, drop_event):
        pix = drop_event.mimeData().data("image/png")
        p = plot_window.getPageNumber()
        page = plot_window.document.basewidget.children[p]
        graph = searchFirstOccurrence(page, 'graph')
        cmd = document.CommandInterface(plot_window.document)
        name = unicode(drop_event.mimeData().data("text/plain"))
        name = name.replace(':/',':').replace('/','_')
        cmd.To(graph.path)
        try:
            cmd.Remove(name)
        except:
            pass
        cmd.Add('imagefile', name=name, autoadd=False)
        cmd.To(name)
        cmd.Set('filename', '{embedded}')
        cmd.Set('embeddedImageData', unicode(b64encode(pix)))    


class VeuszPlotWindow(plotwindow.PlotWindow):
    sigNearestWidget = QtCore.pyqtSignal(object)
    
    def __init__(self, document, parent=None, **kw):
        plotwindow.PlotWindow.__init__(self, document, parent=parent, **kw)
        self.contextmenu = QtGui.QMenu(self)
        self.sigUpdatePage.connect(self.update_page)
        self.navigator = False
        registerImportCommand('MoveToLastPage', self.moveToLastPage)
        self.actionSetTimeout(250, True)
        self.setAcceptDrops(True)
        
    def dragMoveEvent(self, event):
        process_image_dragMoveEvent(event)

    def dropEvent(self, drop_event):
        process_image_dropEvent(self, drop_event)

    def moveToLastPage(self):
        number_of_pages = self.document.getNumberPages()
        self.setPageNumber(number_of_pages - 1)
        
    def set_navigator(self, navigator):
        self.navigator = navigator
        self.sigWidgetClicked.connect(self.navigator.sync_currentwidget)
        
    def widget_menu(self, menu, pos):
        widget = self.identify_widget(pos)
        if widget is None:
            return
        if widget.typename != 'xy':
            return
        dsn = widget.settings.yData
        node = self.document.model.tree.traverse(dsn)
        if not node:
            return
        self.dataset_menu = self.navigator.buildContextMenu(node)
        dsfunc = partial(self.navigator.expand_node_path, node, select=True)
        self.dataset_menu.hovered.connect(dsfunc)
        menu.addMenu(self.dataset_menu)
         
        self.group_menu = self.navigator.buildContextMenu(node.parent)
        grfunc = partial(self.navigator.expand_node_path, node.parent, select=True)
        self.group_menu.hovered.connect(grfunc)
        menu.addMenu(self.group_menu)
        
    def mouseMoveEvent(self, event):
        ret = plotwindow.PlotWindow.mouseMoveEvent(self, event)
        pos = self.mapToScene(event.pos())
        widget = self.identify_widget(pos)
        self.sigNearestWidget.emit(widget)
        return ret
        
    def contextMenuEvent(self, event):
        """Show context menu."""
        menu = QtGui.QMenu()
        for act in self.contextmenu.actions():
            menu.addAction(act)
        pos = self.mapToScene(event.pos())
        self.f = partial(self.edit_properties, pos, False)
        menu.addAction('Properties', self.f)
        self.f1 = partial(self.edit_properties, pos, True)
        menu.addAction('Formatting', self.f1)
        self.fdel = partial(self.delete_widget, pos)
        menu.addAction('Delete selected', self.fdel)
        self.widget_menu(menu, pos)
        
        

        # add some useful entries
        menu.addAction(self.vzactions['view.zoommenu'])
        menu.addSeparator()
        menu.addAction(self.vzactions['view.prevpage'])
        menu.addAction(self.vzactions['view.nextpage'])
        menu.addSeparator()

        # force an update now menu item
        menu.addAction('Force update', self.actionForceUpdate)

        if self.isfullscreen:
            menu.addAction('Close full screen', self.slotFullScreen)
        else:
            menu.addAction(self.vzactions['view.fullscreen'])

        # Update policy submenu
        submenu = menu.addMenu('Updates')
        intgrp = qt4.QActionGroup(self)

        def slotfn(v):
            return lambda: self.actionSetTimeout(v, False)

        # bind interval options to actions
        for intv, text in self.updateintervals:
            act = intgrp.addAction(text)
            act.setCheckable(True)
            fn = slotfn(intv)
# 			fn = veusz.utils.BoundCaller(self.actionSetTimeout, intv)
            self.connect(act, QtCore.SIGNAL('triggered(bool)'), fn)
            if intv == self.interval:
                act.setChecked(True)
            submenu.addAction(act)

        # antialias
        menu.addSeparator()
        act = menu.addAction('Antialias', self.actionAntialias)
        act.setCheckable(True)
        act.setChecked(self.antialias)

        # Selected object specific actions
        # ...
        menu.addSeparator()
        # Export to PDF
        menu.addAction('Export Page', self.slotPageExport)
        menu.addAction('Export All', self.slotDocExport)
        # menu.addAction('Save', self.save_to_file)
        menu.exec_(qt4.QCursor.pos())

    def save_to_file(self):
        name = QtGui.QFileDialog.getSaveFileName(self, _('Save this plot to file'),
                                                 _(
                                                     'runtime.vsz'),
                                                 filter='Veusz (*.vsz);;Images (*.png *.jpg);;Vector (*svg *pdf *eps)')
        name = unicode(name)
        if len(name) == 0:
            return
        f = open(name, 'w')
        self.document.saveToFile(f)
        f.close()
        
    def identify_widget(self, pos):
        widget = self.painthelper.identifyWidgetAtPoint(
            pos.x(), pos.y(), antialias=self.antialias)
        if widget is None:
            # select page if nothing clicked
            widget = self.document.basewidget.getPage(self.pagenumber) 
        return widget      

    def edit_properties(self, pos, frm=False):
        widget = self.identify_widget(pos)
        self.w = treeeditwindow.PropertyList(
            self.document, showformatsettings=frm)
        s = treeeditwindow.SettingsProxySingle(self.document, widget.settings)
        self.w.updateProperties(s)
        self.w.show()
        
    def delete_widget(self, pos):
        widget = self.identify_widget(pos)
        op = OperationWidgetDelete(widget)
        self.document.applyOperation(op)

    dirname_export = False
    filename = ''
    exdialog = False
    def slotDocExport(self):
        """Export the graph."""
        if self.exdialog:
            self.exdialog.hide()
            self.exdialog.close()
            del self.exdialog
        from veusz.dialogs.export import ExportDialog
        dialog = ExportDialog(self, self.document, self.filename)
        self.exdialog= dialog
        dialog.show()
        

    def slotPageExport(self, page_num=-1):
        """Copied from MainWindow. TODO: make this more modular in veusz!"""
        # check there is a page
        if self.document.getNumberPages() == 0:
            qt4.QMessageBox.warning(self, _("Error - Veusz"),
                                    _("No pages to export"))
            return

        # File types we can export to in the form ([extensions], Name)
        fd = qt4.QFileDialog(self, _('Export page'))
        if self.dirname_export:
            fd.setDirectory(self.dirname_export)

        fd.setFileMode(qt4.QFileDialog.AnyFile)
        fd.setAcceptMode(qt4.QFileDialog.AcceptSave)

        # Create a mapping between a format string and extensions
        filtertoext = {}
        # convert extensions to filter
        exttofilter = {}
        filters = []
        # a list of extensions which are allowed
        validextns = []
        formats = document.Export.formats
        for extns, name in formats:
            extensions = " ".join(["*." + item for item in extns])
            # join eveything together to make a filter string
            filterstr = '%s (%s)' % (name, extensions)
            filtertoext[filterstr] = extns
            for e in extns:
                exttofilter[e] = filterstr
            filters.append(filterstr)
            validextns += extns
        fd.setNameFilters(filters)

        # restore last format if possible
        try:
            filt = setdb['export_lastformat']
            fd.selectNameFilter(filt)
            extn = formats[filters.index(filt)][0][0]
        except (KeyError, IndexError, ValueError):
            extn = 'pdf'
            fd.selectNameFilter(exttofilter[extn])

        if self.filename:
            # try to convert current filename to export name
            filename = os.path.basename(self.filename)
            filename = os.path.splitext(filename)[0] + '.' + extn
            fd.selectFile(filename)

        if fd.exec_() == qt4.QDialog.Accepted:
            # save directory for next time
            self.dirname_export = fd.directory().absolutePath()

            filterused = str(fd.selectedFilter())
            setdb['export_lastformat'] = filterused

            chosenextns = filtertoext[filterused]

            filename = fd.selectedFiles()[0]

            self.doExport(filename, validextns, chosenextns, page_num)

    @with_busy_cursor
    def doExport(self, filename, validextns, chosenextns, page_num=-1):
        ext = os.path.splitext(filename)[1][1:]
        if (ext not in validextns) and (ext not in chosenextns):
            filename += "." + chosenextns[0]
        
        if page_num<0:
            page_num=self.getPageNumber()
        export = document.Export(
            self.document,
            filename,
            page_num,
            bitmapdpi=setdb['export_DPI'],
            pdfdpi=setdb['export_DPI_PDF'],
            antialias=setdb['export_antialias'],
            color=setdb['export_color'],
            quality=setdb['export_quality'],
            backcolor=setdb['export_background'],
            svgtextastext=setdb['export_SVG_text_as_text'],
        )

        export.export()

    def update_page(self, *foo):
        """Update the navigator view in order to show colours and styles
        effectively present in the current page"""
        n = self.getPageNumber()
        page = self.document.basewidget.getPage(n)
        if page is None:
            logging.debug('NO PAGE FOUND', n)
        else:
            self.docchangeset = -100 # force plot update for page resizing
            self.document.model.set_page(page.path)

    def setPageNumber(self, page):
        r = plotwindow.PlotWindow.setPageNumber(self, page)
        self.update_page()
        return r
    
    def doPick(self, mouse_position):
        logging.debug('DO PICK', mouse_position)
        plotwindow.PlotWindow.doPick(self, mouse_position)
        plugin.InterceptPlugin.clicked_curve(mouse_position, self.parent())
    



class VeuszPlot(QtGui.QWidget):

    """Simple Veusz graph for live plotting"""
    __pyqtSignals__ = ('smallPlot()', 'bigPlot()')
    vzactions = {}
    documentOpened = qt4.pyqtSignal()
    cmd = False
    ci = False

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.menus = {'edit.select': QtGui.QMenu()}  # fake
        self._menuBar = QtGui.QMenuBar()
        self._menuBar.hide()
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.plot = QtGui.QWidget()
        self.treeedit = QtGui.QWidget()
        self.lay.addWidget(self.plot)
        self.setMinimumSize(180, 180)

    def menuBar(self):  # fake
        return self._menuBar

    def addToolBar(self, *args):
        """This function is required during self.plot instantiation."""
        args[1].hide()
        pass

    def showDialog(self, dialog):
        """Show dialog given."""
        dialog.show()
        self.emit(QtCore.SIGNAL('dialogShown'), dialog)

    def addToolBarBreak(self, *a, **k):
        pass

    def enable_shortcuts(self):
        for action in self.plot.vzactions.itervalues():
            self.addAction(action)

    def set_doc(self, doc=False):
        self.treeedit.close()
        self.lay.removeWidget(self.plot)
        self.plot.hide()
        self.plot.close()
        del self.plot
        # Adding Veusz objects
        if not doc:
            doc = filedata.MisuraDocument()
        self.document = doc
        self._document = self.document
        self.cmd = document.CommandInterface(self.document)
        self.ci = document.CommandInterpreter(self.document)
        self.plot = VeuszPlotWindow(self.document, self)
        self.lay.addWidget(self.plot)

        self.enable_shortcuts()

        # Faking mainwindow
        self.treeedit = treeeditwindow.TreeEditDock(doc, self)
        self.treeedit.hide()
        self.vinit = 0

        # Loading Stylesheet
        if os.path.exists('/opt/misura/misura/client/art/plot.vst'):
            self.ci.run("Load('/opt/misura/misura/client/art/plot.vst')")

        plugin.makeDefaultDoc(self.cmd)

        # Override the zoompage action in order to fit the plot into widget
        # dimension.
        zp = self.plot.vzactions['view.zoompage']
        self.plot.disconnect(
            zp, QtCore.SIGNAL('triggered()'), self.plot.slotViewZoomPage)
        self.plot.connect(zp, QtCore.SIGNAL('triggered()'), self.fitSize)
        self.delayed = QtCore.QTimer()
        self.zoompageAct = zp
        self.plot.sigWidgetClicked.connect(self.treeedit.selectWidget)
        self.treeedit.widgetsSelected.connect(self.plot.selectedWidgets)
        self.treeedit.sigPageChanged.connect(self.plot.setPageNumber)
        self.document.model.sigPageChanged.connect(self.sync_page)

    def sync_page(self, page=-1):
        self.plot.update_page()
        self.fitSize()

    def pauseUpdate(self):
        self.updatePolicy = setting.settingdb['plot_updatepolicy']
        setting.settingdb['plot_updatepolicy'] = 0

    def restoreUpdate(self):
        setting.settingdb['plot_updatepolicy'] = self.updatePolicy

    def delayedUpdate(self):
        self.plot.actionForceUpdate()
        if not self.vinit:
            self.vinit = True
            self.fitSize()

    def showEvent(self, e):
        logging.debug('show event')
        self.fitSize()
#		self.plot.delayed.singleShot(100, self.delayedUpdate)

    def resizeEvent(self, e):
        if not self.cmd:
            # No plot/document defined
            return
        self.fitSize(zoom=True)
        self.plot.actionForceUpdate()
        
    def set_if_differs(self, setpath, value):
        if self.cmd.Get(setpath)!=value:
            self.cmd.Set(setpath, value)
            return True
        return False

    @QtCore.pyqtSignature("fitSize()")
    def fitSize(self, zoom=False):
        """Fit the plot into the widget size.
        `zoom` asks for zooming factor preservation."""
        if not isinstance(self.plot, VeuszPlotWindow):
            logging.debug( 'Cannot fitSize on widget')
            return
        if not zoom and self.plot.zoomfactor!=1.:
            self.plot.slotViewZoom11()
        w = self.plot.width()
        h = self.plot.height()
#         if self.plot.viewtoolbar.isVisible():
#             h -= (self.plot.viewtoolbar.height() + 30)
        w = 1. * w / self.plot.dpi[0] - .2
        h = 1. * h / self.plot.dpi[1] - .2
        self.cmd.To('/')
        
        # If the plot dimension is not sufficient, hide the axes.
        page = self.document.basewidget.getPage(self.plot.getPageNumber())
        if page is None:
            page = self.document.basewidget.children[0]
        g = page.path
        if g.endswith('_report'):
            return
        sw = '{:.1f}in'.format(w)
        sh = '{:.1f}in'.format(h)
        r1 = self.set_if_differs(page.path+'/width', sw)
        r2 = self.set_if_differs(page.path+'/height', sh)
        if not r1 and not r2:
            logging.debug('fitSize: nothing to do')
            return
        logging.debug('fitSize', w, h)
        wg = searchFirstOccurrence(page, 'grid', 1)
        if wg is None:
            wg = searchFirstOccurrence(page, 'graph', 1)
        g = wg.path 
        
        if h < 2 or w < 4:
            self.set_if_differs(g + '/leftMargin', '0.1cm')
            self.set_if_differs(g + '/bottomMargin', '0.1cm')
            self.set_if_differs(g + '/rightMargin', '0.1cm')
            try:
                self.set_if_differs(g + '/x/hide', True)
                self.set_if_differs(g + '/y/hide', True)
            except:
                pass
            self.emit(QtCore.SIGNAL('smallPlot()'))
        else:
            print 'settings for', g
            self.set_if_differs(g + '/leftMargin', '1.5cm')
            self.set_if_differs(g + '/bottomMargin', '1.1cm')
            self.set_if_differs(g + '/rightMargin', '1.4cm')
            try:
                self.set_if_differs(g + '/x/hide', False)
                self.set_if_differs(g + '/y/hide', False)
            except:
                pass
            self.emit(QtCore.SIGNAL('bigPlot()'))
        logging.debug('endfitsize')
        self.emit(QtCore.SIGNAL('fitSize()'))

    def slotDataEdit(self, editdataset=None):
        """Edit existing datasets.
        If editdataset is set to a dataset name, edit this dataset
        """
        dialog = dataeditdialog.DataEditDialog(self, self.document)
        dialog.show()
        if editdataset is not None:
            dialog.selectDataset(editdataset)
        return dialog

    def get_range_of_axis(self, full_axis_name):
        r = self.document.resolveFullWidgetPath(full_axis_name)
        r.computePlottedRange(force=True)
        return r.getPlottedRange()
