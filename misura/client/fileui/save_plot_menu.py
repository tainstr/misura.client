#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Plot persistence on hdf files"""
import os
import functools
from datetime import datetime

from veusz import document
from veusz.utils import pixmapAsHtml
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.csutil import validate_filename
from .. import _
from .. import clientconf

from PyQt4 import QtGui, QtCore


class SavePlotMenu(QtGui.QMenu):

    """Available embedded plots menu"""
    plotChanged = QtCore.pyqtSignal(('QString'))
    versionChanged = QtCore.pyqtSignal(('QString'))
    current_plot_id = False
    doc = False

    def __init__(self, doc, parent=None):
        QtGui.QMenu.__init__(self, parent=parent)
        self.setTitle(_('Plots'))
        self.doc = doc
        self.redraw()
        self.connect(self, QtCore.SIGNAL('aboutToShow()'), self.redraw)
        self.plots = {}

    @property
    def proxy(self):
        if not self.doc:
            return False
        return self.doc.proxy

    def redraw(self):
        self.clear()
        vd = self.proxy.get_plots(render=True)
        vers = self.proxy.get_versions()
        self.plots = vd
        if vd is None:
            return
        logging.debug('Current plot %s', self.current_plot_id)
        self.loadActs = [] # just keep a reference
        for v, info in vd.iteritems():
            logging.debug('Found plot %s %s', v, info[:2])
            p = functools.partial(self.load_plot, v)
            vername = vers.get(info[4], ['???'])[0]
            act = self.addAction(' - '.join((info[0], info[1], vername)), p)
            act.setCheckable(True)
            if info[2]:
                pix = QtGui.QPixmap()
                pix.loadFromData(info[2], 'JPG')
                tooltip = "<html>{}</html>".format(pixmapAsHtml(pix))
                act.setToolTip(tooltip)
            if v == self.current_plot_id:
                act.setChecked(True)
            # Keep in memory
            self.loadActs.append((p, act))
        if len(vd) > 0:
            self.addSeparator()
        act = self.addAction(_('New plot for current version'), self.new_plot)
        self.loadActs.append((self.new_plot, act))
        act = self.addAction(_('New plot in new version'), 
                               functools.partial(self.new_plot, with_version=True))
        self.loadActs.append((self.new_plot, act))
        act = self.addAction(_('Overwrite current plot'), self.save_plot)
        self.loadActs.append((self.save_plot, act))
        if len(vd) == 0:
            act.setEnabled(False)
        if self.current_plot_id:
            act = self.addAction(_('Delete current plot'), self.remove_plot)

    def preview(self, plot_id):
        logging.debug('PREVIEW', plot_id)
        img = self.plots[plot_id][2]
        pix = QtGui.QPixmap()
        pix.loadFromData(img, 'JPG')
        self.lbl = QtGui.QLabel()
        self.lbl.setPixmap(pix)
        self.lbl.show()

    def load_plot_version(self, version_path):
        """Search last occurence of plot with required version"""
        plots = self.proxy.get_plots()
        ok = []
        for plot_id, info in plots.iteritems():
            if info[4] == version_path:
                info = list(info)
                info.append(plot_id)
                info[1] = datetime.strptime(info[1], "%H:%M:%S, %d/%m/%Y")
                ok.append(info)
        if not ok:
            logging.debug('No applicable plot for selected version')
            self.current_plot_id = False
            self.redraw()
            return False
        ok.sort(key=lambda el: el[1])
        ok = ok[-1]
        self.load_plot(ok[-1], load_version=False)

    def load_plot(self, plot_id, load_version=True):
        """Load selected plot"""
        text, attrs = self.proxy.get_plot(plot_id)
        # Try to set the current version to the plot_id
        ver = attrs.get('version', False)
        if load_version and ver and ver != self.proxy.get_version():
            self.proxy.set_version(ver)
            self.versionChanged.emit(self.proxy.get_version())
        # TODO: replace with tempfile
        tmp = 'tmp_load_file.vsz'
        open(tmp, 'w').write(text)
        uid = self.proxy.get_uid()
        path = self.proxy.get_path()
        clientconf.confdb.known_uids[uid] = path
        self.doc.load(tmp)
        os.remove(tmp)
        self.current_plot_id = plot_id

    def save_plot(self, name=False, page=1, with_version=False):
        """Save overwrite plot in current name"""
        if not name:
            plot_id = self.current_plot_id
        else:
            plot_id = validate_filename(name, bad=[' '])
        if with_version:
            r= self.doc.save_version_and_plot(plot_id)
        else:
            r = self.doc.save_plot(self.proxy, plot_id, page, name)
        self.current_plot_id = plot_id
        self.redraw()
        return     

    def remove_plot(self, plot_id=False):
        """Delete current plot or plot_id folder structure"""
        if not plot_id:
            plot_id = self.current_plot_id
        if not plot_id:
            logging.debug('No current plot')
            return False
        node = '/plot/{}'.format(plot_id)
        self.proxy.remove_node(node, recursive=True)
        logging.debug('Removed plot', node)
        self.proxy.flush()
        return True

    def new_plot(self, with_version=False):
        """Create a new plot"""
        # TODO: ask for render and pagenumber
        if with_version:
            title = _('Plot and version name')
            msg = _('Choose a name for this plot and version')
        else:
            title = _('Plot name')
            msg = _('Choose a name for this plot')
        name, st = QtGui.QInputDialog.getText(self, title, msg)
        if not st:
            return False
        r = self.save_plot(name, with_version=with_version)
        if r:
            self.current_plot_id = name

    def event(self, ev):
        """Tooltip handling"""
        if ev.type() == QtCore.QEvent.ToolTip:
            QtGui.QToolTip.showText(
                ev.globalPos(), self.activeAction().toolTip())
        else:
            QtGui.QToolTip.hideText()
        return QtGui.QMenu.event(self, ev)
