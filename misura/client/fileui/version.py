#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Versioning management utilities"""
import functools
from datetime import datetime
import os

from veusz.utils import pixmapAsHtml

from PyQt4 import QtGui, QtCore

from misura.canon.csutil import validate_filename
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from .. import _
from .. import clientconf


class VersionMenu(QtGui.QMenu):

    """Available object versions menu"""
    versionChanged = QtCore.pyqtSignal(('QString'))
    plotChanged = QtCore.pyqtSignal(str, str)
    current_plot_id = False
    doc = False

    def __init__(self, doc, parent=None):
        QtGui.QMenu.__init__(self, parent=parent)
        self.setTitle(_('Version'))
        self.doc = doc
        self.redraw()
        self.aboutToShow.connect(self.redraw)

    @property
    def proxy(self):
        # TODO: submenu for each proxy in doc
        if not self.doc:
            return False
        return self.doc.proxy

    def add_plot_menu(self, version, menu):
        p = self.proxy.get_plots(version=version, render=True)
        if not p:
            logging.debug('No plots for selected version', version)
            return False
        menu.addSeparator()
        if version == self.current:
            menu.addAction(_('Save new plot'), self.new_plot)
        for plot_id, (title, date, render, render_format) in p.iteritems():
            pmenu = menu.addMenu(' - '.join((title, date)))
            act = pmenu.addAction(_('Load plot'),
                                  functools.partial(self.load_plot, version, plot_id))
            pix = QtGui.QPixmap()
            pix.loadFromData(render, render_format.upper())
            tooltip = "<html>{}</html>".format(pixmapAsHtml(pix))
            act.setCheckable(True)
            print 'setting checked', self.current_plot_id, repr(plot_id)
            act.setChecked(self.current_plot_id == plot_id)
            act.setToolTip(tooltip)
            if version == self.current:
                pmenu.addAction(_('Overwrite plot'),
                                functools.partial(self.load_plot, version, plot_id))
            pmenu.addAction(_('Delete plot'),
                            functools.partial(self.remove_plot, version, plot_id))

    def load_plot(self, version, plot_id):
        if version != self.current:
            self.load_version(version, latest_plot=False)
        text, attrs = self.proxy.get_plot(plot_id)
        # Try to set the current version to the plot_id
        ver = attrs.get('version', False)
        # TODO: replace with tempfile
        tmp = 'tmp_load_file.vsz'
        open(tmp, 'w').write(text)
        uid = self.proxy.get_uid()
        path = self.proxy.get_path()
        clientconf.confdb.known_uids[uid] = path
        self.doc.load(tmp)
        os.remove(tmp)
        self.current_plot_id = plot_id
        self.plotChanged.emit(self.current, plot_id)

    def save_plot(self, name=False, page=1):
        """Save overwrite plot in current name"""
        if not name:
            plot_id = self.current_plot_id
        else:
            plot_id = validate_filename(name, bad=[' '])
        r = self.doc.save_plot(self.proxy, plot_id, page, name)
        self.current_plot_id = plot_id
        self.redraw()
        return

    def load_latest_plot(self):
        """Search last occurence of plot with required version"""
        plots = self.proxy.get_plots()
        ok = []
        for plot_id, info in plots.iteritems():
            info = list(info)
            info.append(plot_id)
            info[1] = datetime.strptime(info[1], "%H:%M:%S, %d/%m/%Y")
            ok.append(info)
        if not ok:
            logging.debug('No saved plots in current version', self.current)
            self.current_plot_id = False
            self.redraw()
            return False
        ok.sort(key=lambda el: el[1])
        ok = ok[-1]
        logging.debug('Loading latest plot for version', self.current, ok[-1])
        self.load_plot(self.current, ok[-1])

    def remove_plot(self, plot_id=False):
        """Delete current plot or plot_id folder structure"""
        if not plot_id:
            plot_id = self.current_plot_id
        if not plot_id:
            logging.debug('No current plot')
            return False
        node = self.proxy.versioned('/plot/{}'.format(plot_id))
        self.proxy.remove_node(node, recursive=True)
        logging.debug('Removed plot', node)
        self.proxy.flush()
        return True

    def new_plot(self):
        """Create a new plot"""
        # TODO: ask for render and pagenumber
        title = _('Plot name')
        msg = _('Choose a name for this plot')
        name, st = QtGui.QInputDialog.getText(self, title, msg)
        if not st:
            return False
        r = self.save_plot(name)

    def overwrite_plot(self):
        self.save_plot(name=self.current_plot_id)

    def redraw(self):
        self.clear()
        vd = self.proxy.get_versions()
        logging.debug('Got info', vd)
        if vd is None:
            return
        self.current = self.proxy.get_version()
        logging.debug('Current version', self.current)
        self.loadActs = []
        for v, info in vd.iteritems():
            logging.debug('Found version', v, info)
            p = functools.partial(self.load_version, v)
            vermenu = self.addMenu(' - '.join(info))
            act = vermenu.addAction(_('Load version'), p)
            act.setCheckable(True)
            if v == self.current:
                act.setChecked(True)
            # Keep in memory
            self.loadActs.append((p, act))
            self.add_plot_menu(v, vermenu)
        if len(vd) > 0:
            self.addSeparator()
        act = self.addAction(_('New version and plot'), self.new_version)
        self.loadActs.append((self.new_version, act))
        self.actOverwrite = self.addAction(
            _('Overwrite current version and plot'), self.save_version)
        self.actOverwrite.setEnabled(bool(self.current))
        self.loadActs.append((self.save_version, self.actOverwrite))
        self.actRemove = self.addAction(
            _('Delete current'), self.remove_version)
        self.actRemove.setEnabled(bool(self.current))
        self.actValidate = self.addAction(_('Check signature'), self.signature)

    def load_version(self, v, latest_plot=True):
        """Load selected version"""
        self.proxy.set_version(v)
        v = self.proxy.get_version()
        self.actRemove.setEnabled(bool(v))
        self.actOverwrite.setEnabled(bool(v))
        self.current = v
        if latest_plot:
            self.load_latest_plot()
        self.versionChanged.emit(v)

    def save_version(self):
        """Save configuration in current version"""
        # Try to create a new version
        if self.proxy.get_version() == '':
            if not self.new_version():
                QtGui.QMessageBox.critical(
                    self, _("Not saved"), _("Cannot overwrite original version"))
                return False
            return True
        self.current = self.proxy.get_version()
        version_name, version_date = self.proxy.get_versions()[self.current]
        self.doc.save_version_and_plot(version_name)
        self.current_plot_id = version_name
        self.actRemove.setEnabled(True)
        self.actOverwrite.setEnabled(True)
        return True

    def new_version(self):
        """Create a new version"""
        name, st = QtGui.QInputDialog.getText(
            self, _('Version name'), _('Choose a name for this version'))
        if not st:
            return False
        self.proxy.create_version(unicode(name))
        self.save_version()
        return True

    def remove_version(self):
        """Delete current plot or plot_id folder structure"""
        ver = self.proxy.get_version()
        if not ver:
            logging.debug('No current version to be removed')
            self.actRemove.setEnabled(False)
            return False
        self.proxy.remove_version(ver)
        logging.debug('Removed version', ver)
        # Return to original version
        self.load_version(0)
        return True

    def signature(self):
        """Check file signature"""
        r = self.proxy.verify()
        if not r:
            QtGui.QMessageBox.critical(
                self, _("Signature check failed"), _("Test data cannot be trusted."))
        else:
            QtGui.QMessageBox.information(
                self, _("Signature check succeeded"), _("Test data is genuine."))
