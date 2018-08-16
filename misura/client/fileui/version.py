#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Versioning management utilities"""
import functools
from datetime import datetime
import os
from traceback import format_exc
from veusz.utils import pixmapAsHtml

from PyQt4 import QtGui, QtCore

from misura.canon.csutil import validate_filename
from misura.canon.logger import get_module_logging
from misura.client.widgets.active import RunMethod
logging = get_module_logging(__name__)

from .. import _
from .. import clientconf


class PlotSubMenu(QtGui.QMenu):

    def __init__(self, version_menu, version, plot_id, title, date, render=False, render_format=False, parent=False):
        QtGui.QMenu.__init__(self, parent=parent)
        self.setTitle(' - '.join((title, date)))
        self.version_menu = version_menu
        self.version = version
        self.plot_id = plot_id
        self._title = title
        self.date = date
        self.render = render
        self.render_format = render_format
        self.menuAction().hovered.connect(self.redraw)

    def redraw(self):
        self.clear()
        act = self.addAction(_('Load plot'), self.load_plot)
        if self.render and self.render_format:
            pix = QtGui.QPixmap()
            pix.loadFromData(self.render, self.render_format.upper())
            tooltip = "<html>{}</html>".format(pixmapAsHtml(pix))
            act.setCheckable(True)
            act.setChecked(self.version_menu.current_plot_id == self.plot_id)
            act.setToolTip(tooltip)
        if self.version == self.version_menu.current:
            self.addAction(
                _('Overwrite plot'), self.version_menu.overwrite_plot)
        self.addAction(_('Delete plot'), self.remove_plot)

    def load_plot(self):
        self.version_menu.load_plot(self.version, self.plot_id)

    def remove_plot(self):
        self.version_menu.remove_plot(self.version, self.plot_id)

    def event(self, ev):
        """Tooltip preview handling"""
        if ev.type() == QtCore.QEvent.ToolTip and self.activeAction():
            QtGui.QToolTip.showText(
                ev.globalPos(), self.activeAction().toolTip())
        else:
            QtGui.QToolTip.hideText()
        return QtGui.QMenu.event(self, ev)


class VersionMenu(QtGui.QMenu):

    """Available object versions menu"""
    versionChanged = QtCore.pyqtSignal(('QString'))
    plotChanged = QtCore.pyqtSignal(str, str)
    versionSaved = QtCore.pyqtSignal(str)
    plotSaved = QtCore.pyqtSignal(str)
    current_plot_id = False
    doc = False
    _proxy = False

    def __init__(self, doc, proxy=False, parent=None):
        QtGui.QMenu.__init__(self, parent=parent)
        self.setTitle(_('Version'))
        self.doc = doc
        self._proxy = proxy
        self.aboutToShow.connect(self.redraw)

    @property
    def proxy(self):
        # TODO: submenu for each proxy in doc
        if self._proxy:
            return self._proxy
        if not self.doc:
            return False
        return self.doc.proxy

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
        self.plotSaved.emit(plot_id)
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

    def remove_plot(self, version=False, plot_id=False):
        """Delete current plot or plot_id folder structure"""
        if not plot_id:
            plot_id = self.current_plot_id
        if not version:
            version = self.current
        if not plot_id or not version:
            logging.debug('No current plot or version')
            return False
        node = self.proxy.versioned(
            '/plot/{}'.format(plot_id), version=version)
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

    def add_plot_menu(self, version, menu):
        if version == self.current:
            menu.addAction(_('Save new plot'), self.new_plot)
        p = self.proxy.get_plots(version=version, render=True)
        if not p:
            logging.debug('No plots for selected version', version)
            return False
        menu.addSeparator()
        for plot_id, (title, date, render, render_format) in p.iteritems():
            pmenu = PlotSubMenu(self, version, plot_id, title,
                                date, render, render_format, parent=menu)
            menu.addMenu(pmenu)

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
            vmact = vermenu.menuAction()
            act = vermenu.addAction(_('Load version'), p)
            act.setCheckable(True)
            if v == self.current:
                act.setChecked(True)
                vmact.setCheckable(True)
                vmact.setChecked(True)
            else:
                vmact.setCheckable(False)
            # Keep in memory
            self.loadActs.append((p, act))
            if v:
                vermenu.addAction(_('Delete version'), 
                                  functools.partial(self.remove_version, v))
                vermenu.addAction(_('Overwrite version'), 
                                    functools.partial(self.save_version, v))
                self.add_plot_menu(v, vermenu)
        if len(vd) > 0:
            self.addSeparator()
        act = self.addAction(_('New version and plot'), self.new_version)
        self.loadActs.append((self.new_version, act))
        self.actValidate = self.addAction(_('Check signature'), self.signature)

    def load_version(self, v, latest_plot=True):
        """Load selected version"""
        w = self.proxy.writable()
        if not w:
            self.proxy.reopen(mode='a')
        self.proxy.set_version(v)
        if not w:
            self.proxy.reopen(mode='r')
        v = self.proxy.get_version()
        self.current = v
        if latest_plot:
            self.load_latest_plot()
        logging.debug('load_version', v)
        self.versionChanged.emit(v)

    def save_version(self, version_id=False, nosync=True):
        """Save configuration in current version"""
        # Try to create a new version
        logging.debug('save_version', version_id)
        if not version_id:
            version_id = self.proxy.get_version()
        if version_id in ('', u''):
            logging.debug('Asking a new version name', repr(version_id))
            if not self.new_version():
                QtGui.QMessageBox.critical(
                    self, _("Not saved"), _("Cannot overwrite original version"))
                return False
            return True
        logging.debug('save_version', repr(version_id))
        vers = self.proxy.get_versions()
        version_name, version_date = vers[version_id]
        pid = 'Save: {}'.format(version_name)
        
        self.thread = RunMethod(self.doc.save_version_and_plot, version_name, pid=pid)
        self.thread.pid = pid
        self.thread.notifier.done.connect(functools.partial(self.callback_save, version_name))
        if nosync:
            self.thread.do()
        else:
            logging.debug('Saving synchronously...')
            self.thread.run()
        return True
        
    def callback_save(self, version_name):
        logging.debug('callback_save', version_name)
        self.current_plot_id = version_name
        self.current = self.proxy.get_version()
        self.versionSaved.emit(self.current)      

    def new_version(self):
        """Create a new version"""
        qid = QtGui.QInputDialog(self)
        qid.setInputMode(0)
        qid.setWindowTitle(_('Version name'))
        qid.setLabelText(_('Choose a name for this version'))
        qid.setInputMethodHints(QtCore.Qt.ImhEmailCharactersOnly)
        st = qid.exec_()
        if not st:
            return False
        name = qid.textValue()
        try:
            self.proxy.create_version(unicode(name).encode('ascii', 'replace'))
            self.save_version()
            return True
        except:
            QtGui.QMessageBox.information(self, _('Could not save version'),
                    _('An error occurred while saving version:\n{}').format(format_exc()))
            return False
            
        return True

    def remove_version(self, version=False):
        """Delete current plot or plot_id folder structure"""
        if not version:
            version = self.proxy.get_version()
        if not version:
            logging.debug('No current version can be removed')
            self.actRemove.setEnabled(False)
            return False
        try:
            self.proxy.remove_version(version)
            logging.debug('Removed version', version)
        except:
            self.log.error('Could not remove version:', format_exc())
            QtGui.QMessageBox.information(self, _('Could not remove version'),format_exc())
            return False
        # Return to original version
        if version == self.current:
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
            
class MultiVersionMenu(QtGui.QMenu):
    def __init__(self, doc, parent=None):
        QtGui.QMenu.__init__(self, parent=parent)
        self.setTitle(_('Version'))
        self.doc = doc
        self.menuAction().hovered.connect(self.redraw)
    
    def redraw(self):
        self.clear()
        for fn, proxy in self.doc.proxies.iteritems():
            m = VersionMenu(self.doc, proxy, self)
            m.setTitle(os.path.basename(fn))
            self.addMenu(m)
