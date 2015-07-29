#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple plotting for browser and live acquisition."""
import os
from misura.canon.logger import Log as logging
from veusz import qtall as qt4
from PyQt4 import QtGui, QtCore


from .. import filedata, plugin
from .. import _
MAX = 10**5
MIN = -10**5
import veusz.setting.settingdb as setdb
import veusz.windows.treeeditwindow as treeeditwindow
import veusz.document as document
from veusz.dialogs import dataeditdialog

import veusz.windows.plotwindow as plotwindow
import veusz.setting as setting

from functools import partial


def _(text, disambiguation=None, context='PlotWindow'):
    """Translate text."""
    return qt4.QCoreApplication.translate(context, text, disambiguation)


class VeuszPlotWindow(plotwindow.PlotWindow):

    def __init__(self, document, parent=None):
        plotwindow.PlotWindow.__init__(self, document, parent)
        self.contextmenu = QtGui.QMenu(self)
        self.sigUpdatePage.connect(self.update_page)

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
            return lambda: self.actionSetTimeout(v)

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
        menu.addAction('Export', self.slotFileExport)
        menu.exec_(qt4.QCursor.pos())

    def edit_properties(self, pos, frm=False):
        widget = self.painthelper.identifyWidgetAtPoint(
            pos.x(), pos.y(), antialias=self.antialias)
        if widget is None:
            # select page if nothing clicked
            widget = self.document.basewidget.getPage(self.pagenumber)
        self.w = treeeditwindow.PropertyList(
            self.document, showformatsettings=frm)
        s = treeeditwindow.SettingsProxySingle(self.document, widget.settings)
        self.w.updateProperties(s)
        self.w.show()

    dirname_export = False
    filename = False

    def slotFileExport(self):
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

            # show busy cursor
            qt4.QApplication.setOverrideCursor(qt4.QCursor(qt4.Qt.WaitCursor))

            filename = fd.selectedFiles()[0]

            # Add a default extension if one isn't supplied
            # this is the extension without the dot
            ext = os.path.splitext(filename)[1][1:]
            if (ext not in validextns) and (ext not in chosenextns):
                filename += "." + chosenextns[0]

            export = document.Export(
                self.document,
                filename,
                self.getPageNumber(),
                bitmapdpi=setdb['export_DPI'],
                pdfdpi=setdb['export_DPI_PDF'],
                antialias=setdb['export_antialias'],
                color=setdb['export_color'],
                quality=setdb['export_quality'],
                backcolor=setdb['export_background'],
                svgtextastext=setdb['export_SVG_text_as_text'],
            )

# 			try:
            export.export()
# 			except (RuntimeError, EnvironmentError) as e:
# 				if isinstance(e, EnvironmentError):
# 					msg = cstrerror(e)
# 				else:
# 					msg = cstr(e)
#
# 				qt4.QApplication.restoreOverrideCursor()
# 				qt4.QMessageBox.critical(
# 					self, _("Error - Veusz"),
# 					_("Error exporting to file '%s'\n\n%s") %
# 					(filename, msg))
# 			else:
# 				qt4.QApplication.restoreOverrideCursor()

    def update_page(self, *foo):
        """Update the navigator view in order to show colours and styles 
        effectively present in the current page"""
        n = self.getPageNumber()
        page = self.document.basewidget.getPage(n)
        if page is None:
            logging.debug('%s %s', 'NO PAGE FOUND', n)
            return
        logging.debug('%s %s', 'update_page', page.path)
        self.document.model.set_page(page.path)


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
        self.viewtoolbar = args[1]
        self.lay.addWidget(args[1])
        self.viewtoolbar.hide()

    def showDialog(self, dialog):
        """Show dialog given."""
        dialog.show()
        self.emit(QtCore.SIGNAL('dialogShown'), dialog)

    def addToolBarBreak(self, *a, **k):
        pass

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
        self.cmd = document.CommandInterface(self.document)
        self.ci = document.CommandInterpreter(self.document)
        self.plot = VeuszPlotWindow(self.document, self)
        self.lay.addWidget(self.plot)

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
        logging.debug('%s', 'show event')
        self.fitSize()
#		self.plot.delayed.singleShot(100, self.delayedUpdate)

    def resizeEvent(self, e):
        if not self.cmd:
            # No plot/document defined
            return
        self.fitSize(zoom=True)
        self.plot.actionForceUpdate()

    @QtCore.pyqtSignature("fitSize()")
    def fitSize(self, zoom=False):
        """Fit the plot into the widget size.
        `zoom` asks for zooming factor preservation."""
        if not isinstance(self.plot, VeuszPlotWindow):
            logging.debug('%s', 'Cannot fitSize on widget')
            return
        if not zoom:
            self.plot.slotViewZoom11()
        w = self.plot.width()
        h = self.plot.height()
        if self.plot.viewtoolbar.isVisible():
            h -= (self.plot.viewtoolbar.height() + 30)
        w = 1. * w / self.plot.dpi[0] - .2
        h = 1. * h / self.plot.dpi[1] - .2
        self.cmd.To('/')
        self.cmd.Set('/width', str(w) + 'in')
        self.cmd.Set('/height', str(h) + 'in')

        logging.debug('%s %s %s', 'fitSize', w, h)
        # If the plot dimension is not sufficient, hide the axes.
        page = self.document.basewidget.getPage(self.plot.getPageNumber())
        g = page.name
        if g == 'time':
            g = '/time/time'
        elif g == 'temperature':
            g = '/temperature/temp'
        if h < 2 or w < 4:
            self.cmd.Set(g + '/leftMargin', '0.1cm')
            self.cmd.Set(g + '/bottomMargin', '0.1cm')
            self.cmd.Set(g + '/rightMargin', '0.1cm')
            try:
                self.cmd.Set(g + '/x/hide', True)
                self.cmd.Set(g + '/y/hide', True)
            except:
                pass
            self.emit(QtCore.SIGNAL('smallPlot()'))
        else:
            self.cmd.Set(g + '/leftMargin', '1.5cm')
            self.cmd.Set(g + '/bottomMargin', '1.1cm')
            self.cmd.Set(g + '/rightMargin', '1.4cm')
            try:
                self.cmd.Set(g + '/x/hide', False)
                self.cmd.Set(g + '/y/hide', False)
            except:
                pass
            self.emit(QtCore.SIGNAL('bigPlot()'))
        logging.debug('%s', 'endfitsize')
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
