#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Versioning management utilities"""
from misura.canon.logger import Log as logging
from .. import _
import functools
from PyQt4 import QtGui, QtCore


class VersionMenu(QtGui.QMenu):

    """Available object versions menu"""
    versionChanged = QtCore.pyqtSignal(('QString'))

    def __init__(self, doc, parent=None):
        QtGui.QMenu.__init__(self, parent=parent)
        self.setTitle(_('Version'))
        self.doc = doc
        #TODO: submenu for each proxy in doc
        self.proxy = doc.proxy
        self.redraw()
        self.connect(self, QtCore.SIGNAL('aboutToShow()'), self.redraw)

    def redraw(self):
        self.clear()
        vd = self.proxy.get_versions()
        logging.debug('%s %s', 'Got info', vd)
        if vd is None:
            return
        cur = self.proxy.get_version()
        logging.debug('%s %s', 'Current version', cur)
        self.loadActs = []
        for v, info in vd.iteritems():
            logging.debug('%s %s %s', 'Found version', v, info)
            p = functools.partial(self.load_version, v)
            act = self.addAction(' - '.join(info), p)
            act.setCheckable(True)
            if v == cur:
                act.setChecked(True)
            # Keep in memory
            self.loadActs.append((p, act))
        if len(vd) > 0:
            self.addSeparator()
        act = self.addAction(_('New version'), self.new_version)
        self.loadActs.append((self.new_version, act))
        act = self.addAction(_('Save version and plot'), self.save_version)
        self.loadActs.append((self.save_version, act))
        self.actRemove = self.addAction(_('Delete version'), self.remove_version)
        self.actRemove.setEnabled(bool(cur))
        self.actValidate = self.addAction(_('Check signature'), self.signature)

    def load_version(self, v):
        """Load selected version"""
        self.proxy.set_version(v)
        v = self.proxy.get_version()
        self.versionChanged.emit(v)
        self.actRemove.setEnabled(bool(v))

    def save_version(self):
        """Save configuration in current version"""
        # Try to create a new version
        if self.proxy.get_version() == '':
            if not self.new_version():
                QtGui.QMessageBox.critical(
                    self, _("Not saved"), _("Cannot overwrite original version"))
                return False
        version_name, version_date = self.proxy.get_versions()[self.proxy.get_version()]
        self.doc.save_version_and_plot(version_name)
        self.actRemove.setEnabled(True)
        return True

    def new_version(self):
        """Create a new version"""
        name, st = QtGui.QInputDialog.getText(
            self, _('Version name'), _('Choose a name for this version'))
        if not st:
            return False
        self.proxy.create_version(unicode(name))
        self.actRemove.setEnabled(True)
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
