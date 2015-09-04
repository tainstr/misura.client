#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple plotting for browser and live acquisition."""
from misura.canon.logger import Log as logging
from misura.client import plugin
from misura.canon import csutil
from veuszplot import VeuszPlot
from PyQt4 import QtGui, QtCore

qt4 = QtGui

MAX = 10**5
MIN = -10**5


hidden_curves = ['iA', 'iB', 'iC', 'iD', 'xmass', 'ymass']


class Plot(VeuszPlot):
    doc = False
    nav = False
    idx = 0
    t = 0
    visibleCurves = []

    def __init__(self, parent=None):
        VeuszPlot.__init__(self, parent=parent)

    def set_doc(self, doc):
        VeuszPlot.set_doc(self, doc)
        self.doc = doc
        self.idx = 0
        for g in ['/time/time', '/temperature/temp']:
            self.cmd.To(g)
            self.cmd.Set('topMargin', '0.1cm')
            self.cmd.Add('line', name='idx')
            self.cmd.To('idx')
            self.cmd.Set('mode', 'length-angle')
            self.cmd.Set('positioning', 'relative')
            self.cmd.Set('angle', 90.)
            self.cmd.Set('length', 1.)
            self.cmd.Set('xPos', 0.)
            self.cmd.Set('yPos', 1.)
            self.cmd.Set('clip', True)
            self.cmd.Set('Line/color', 'red')
            self.cmd.Set('Line/width', '2pt')
            self.cmd.To('..')

        self.reset()
        self.default_plot()
        self.idx_connect()

    @property
    def model(self):
        return self.document.model

    def idx_connect(self):
        """Reconnect index line motion events"""
        wg = self.doc.resolveFullWidgetPath('/temperature/temp/idx')
        wg.settings.get('xPos').setOnModified(self.move_line_temp)
        wg = self.doc.resolveFullWidgetPath('/time/time/idx')
        wg.settings.get('xPos').setOnModified(self.move_line_time)

    def idx_disconnect(self):
        """Disconnect index line motion events"""
        wg = self.doc.resolveFullWidgetPath('/temperature/temp/idx')
        try:
            wg.settings.get('xPos').removeOnModified(self.move_line_temp)
        except:
            pass
        wg = self.doc.resolveFullWidgetPath('/time/time/idx')
        try:
            wg.settings.get('xPos').removeOnModified(self.move_line_time)
        except:
            pass

    def reset(self):
        # Main context menu
        self.plot.contextmenu = QtGui.QMenu(self)

        # Axes management
        self.axesMenu = self.plot.contextmenu.addMenu('Axes')
        self.axesMenus = {}  # curvename: axes submenu
        self.visibleAxes = []  # axes names
        # TODO: visibleCurves now overlaps with Hierarchy
        # visible/hidden/available mechanism
        self.visibleCurves = []  # curve names
        self.blockedAxes = {}  # curvename: curvename
        self.axesActions = {}  # curvename: action

        # Curves management
        self.curvesMenu = self.plot.contextmenu.addMenu('Curves')
        self.curveActions = {}
        self.connect(self.curvesMenu, QtCore.SIGNAL(
            'aboutToShow()'), self.updateCurvesMenu)
        self.connect(self.axesMenu, QtCore.SIGNAL(
            'aboutToShow()'), self.updateCurveActions)
        self.curveMap = {}
        self.curveNames = {}

        # Scale management
        self.viewMenu = self.plot.contextmenu.addMenu('View')
        self.actByTime = self.viewMenu.addAction('By time', self.byTime)
        self.actByTemp = self.viewMenu.addAction('By Temperature', self.byTemp)
        for act in [self.actByTime, self.actByTemp]:
            act.setCheckable(True)
        self.byTime()

        self.plot.contextmenu.addAction('Reset', self.reset)
        self.plot.contextmenu.addAction('Update', self.update)
        self.plot.contextmenu.addAction('Save to...', self.save_to_file)
        logging.debug('%s %s %s', 'Calling reload data on document',
                      self.document, self.document.filename)
        self.document.reloadData()
        self.model.refresh()
        self.emit(QtCore.SIGNAL('reset()'))

    def default_plot(self):
        logging.debug(
            '%s %s', 'APPLY DEFAULT PLOT PLUGIN', self.document.data.keys())
        p = plugin.DefaultPlotPlugin()
        r = p.apply(self.cmd, {'dsn': self.document.data.keys()})
        self.curveNames.update(r)
        self.visibleCurves += r.keys()
        # FIXME: propagate to tree

    def byTime(self):
        self.plot.setPageNumber(1)
        logging.debug('%s %s', 'byTime', self.plot.getPageNumber())
        self.actByTime.setChecked(True)
        self.actByTemp.setChecked(False)
        self.doc.model.set_page('/time')

    def byTemp(self):
        self.plot.setPageNumber(0)
        logging.debug('%s %s', 'byTemp', self.plot.getPageNumber())
        self.actByTime.setChecked(False)
        self.actByTemp.setChecked(True)
        self.doc.model.set_page('/temperature')

    def hide_show(self, name=False, do=None, update=False, emit=True):
        """`do`: None, check; True, show; False, hide"""
        self.emit(QtCore.SIGNAL('hide_show(QString)'), name)

    def isSectionHidden(self, i=False, col=False):
        if not col:
            col = self.doc.header[i]
        return col in self.visibleCurves

    def updateCurvesMenu(self):
        logging.debug('%s %s', 'updateCurvesMenu', self.document.data.keys())
        self.doc.model.set_page(
            self.doc.basewidget.children[self.plot.pagenumber].path)
        hsf = lambda name: self.hide_show(name, update=True)
        self.load_map, self.avail_map = self.model.build_datasets_menu(
            self.curvesMenu, hsf)
        return

    def updateCurveActions(self):
        logging.debug('%s', 'UPDATE CURVE ACTIONS')
        self.doc.model.set_page(
            self.doc.basewidget.children[self.plot.pagenumber].path)
        self.axesMenu.clear()
        self.axesMenus = self.model.build_axes_menu(self.axesMenu)

    def reloadData(self, update=True):
        self.pauseUpdate()
        if update:
            self.doc.update()
        else:
            dsnames = self.doc.reloadData()
        if len(dsnames) == 0:
            logging.debug('%s', 'No data to reload')
            return
        self.updateCurvesMenu()
        if not update:
            self.set_idx(0)
        self.restoreUpdate()
        return dsnames

    def update(self):
        """Add new points to current datasets and save a temporary file"""
        self.reloadData(update=True)
        self.set_idx()

    def save_to_file(self):
        name = QtGui.QFileDialog.getSaveFileName(self, _('Save this plot to file'),
                                                 _(
                                                     'Choos a filename and format where to save the file.'),
                                                 filter='Veusz (*.vsz);;Images (*.png *.jpg);;Vector (*svg *pdf *eps)')
        name = unicode(name)
        if len(name) == 0:
            logging.debug('%s %s', 'cancelled', name)
            return
        logging.debug('%s %s', 'Saving to', name)
        f = open(name, 'w')
        self.document.saveToFile(f)
        f.close()

    def set_idx(self, seq=-1):
        """Moves the position line according to the requested point sequence index."""
        self.idx_disconnect()
        if seq < 0:
            seq = self.idx
        for g, dsn in (('/time/time/', '0:t'), ('/temperature/temp/', '0:kiln/T')):
            logging.debug('%s', self.document.data.keys())
            ds = self.document.data[dsn]
            if seq >= len(ds.data):
                return
            xval = ds.data[seq]
            xax = self.document.resolveFullWidgetPath(g + 'x')
            xax.computePlottedRange(force=True)
            rg = xax.getPlottedRange()
            # Calc relative position with respect to X axis
            rel = (xval - rg[0]) / (rg[1] - rg[0])
            logging.debug('%s %s %s %s %s %s', 'Red bar relative position:',
                          rel, xval, rg, xax.autorange, xax.plottedrange)
            self.cmd.To(g + 'idx')
            self.cmd.Set('xPos', rel)
            self.cmd.Set('length', 1.)
        self.idx = seq
        self.idx_connect()

    def set_time(self, t):
        """Moves the position line according to the requested point in time"""
        self.t = t
        idx = csutil.find_nearest_val(
            self.document.data['0:t'].data, t, seed=self.idx)
        logging.debug('%s', 'Setting time t')
        self.set_idx(idx)

    def move_line(self, g):
        """Get relative position of index line"""
        wg = self.doc.resolveFullWidgetPath(g + '/idx')
        xax = self.document.resolveFullWidgetPath(g + '/x')
        rg = xax.getPlottedRange()
        rel = wg.settings.xPos[0] * (rg[1] - rg[0]) + rg[0]
        return rel

    def move_line_time(self):
        """Index line was moved on time-based plot"""
        rel = self.move_line('/time/time')
        self.emit(QtCore.SIGNAL('move_line(float)'), rel)

    def move_line_temp(self):
        """Index line was moved on temperature-based plot"""
        rel = self.move_line('/temperature/temp')
        # Convert relative position with respect to temperature to a time value
        # (cooling ramps will be discarted)
        idx = csutil.find_nearest_val(
            self.document.data['0:kiln/T'].data, rel, seed=self.idx)
        t = self.document.data['0:t'].data[idx]
        self.emit(QtCore.SIGNAL('move_line(float)'), t)
