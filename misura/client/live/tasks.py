#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Pending tasks feedback"""
from traceback import format_exc
import functools
import threading

from misura.canon.logger import Log as logging
from misura.canon.csutil import lockme
from misura.client import _
from misura.client.sync import SyncWidget

from PyQt4 import QtGui, QtCore


class PendingTasks(QtGui.QWidget):
    server = False
    progress = False
    ch = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.lay = QtGui.QVBoxLayout(self)
        self.setLayout(self.lay)
        self.setWindowTitle(_('Remote Pending Tasks'))

    def __len__(self):
        if self.progress is False:
            return 0
        r = len(self.progress.prog)
        return r

    def set_server(self, server):
        if not server:
            return False
        self.server = server.copy()
        self.server.connect()
        server = self.server
        # Clean the layout
        if self.progress:
            try:
                self.progress.hide()
                self.progress.unregister()
            except:
                logging.debug(
                    'While removing old progress... \n%s', format_exc())
            finally:
                self.progress = False
        from ..widgets import RoleProgress
        prop = server.gete('progress')
        self.progress = RoleProgress(server, server, prop, parent=self)
        self.progress.force_update = True
        self.progress.label_widget.hide()
        self.lay.addWidget(self.progress)
        self.connect(self.progress, QtCore.SIGNAL(
            'changed()'), self.update, QtCore.Qt.QueuedConnection)
        self.connect(self.progress, QtCore.SIGNAL(
            'selfchanged'), self.update, QtCore.Qt.QueuedConnection)
        self.update()

    def update(self, *a, **k):
        len(self)
        self.ch.emit()


class LocalTasks(QtGui.QWidget):

    """Global server 'progress' option widget. This is a RoleIO pointing to the real 'Progress'-type option being performed"""
    ch = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self._lock = threading.Lock()
        self.lay = QtGui.QHBoxLayout()
        self.setLayout(self.lay)
        self.setWindowTitle(_('Local Operations in Progress'))
        # Base widget
        self.bw = QtGui.QWidget(parent=self)
        self.blay = QtGui.QVBoxLayout()
        self.bw.setLayout(self.blay)
        self.log = QtGui.QTextEdit(parent=self)
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(self.log.NoWrap)
        self.log.setFont(QtGui.QFont('TypeWriter',  7, 50, False))
        self.log.hide()
        self.more = QtGui.QPushButton(_('Log'), parent=self)
        self.connect(self.more, QtCore.SIGNAL('clicked()'), self.toggle_log)

        # Progress bars widget
        self.mw = QtGui.QWidget(parent=self)
        self.mlay = QtGui.QVBoxLayout()
        self.mw.setLayout(self.mlay)
        # Populate the base widget with progress widget, more button, log
        # window
        self.blay.addWidget(self.mw)
        self.blay.addWidget(self.more)
        self.blay.addWidget(self.log)

        self.lay.addWidget(self.bw)

        self.prog = {}

        self.connect(self, QtCore.SIGNAL('jobs(int)'), self._jobs)
        self.connect(self, QtCore.SIGNAL('jobs(int,QString)'), self._jobs)

        self.connect(
            self, QtCore.SIGNAL('job(int,QString,QString)'), self._job)
        self.connect(self, QtCore.SIGNAL('job(int,QString)'), self._job)
        self.connect(self, QtCore.SIGNAL('job(int)'), self._job)

        self.connect(self, QtCore.SIGNAL('sig_done(QString)'),
                     self._done, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('sig_done0()'), self._done,  QtCore.Qt.QueuedConnection)
        logging.debug('%s', 'LocalTasks initialized')

    def __len__(self):
        return len(self.prog)

    def toggle_log(self):
        if self.log.isVisible():
            self.log.hide()
            self.mlay.removeWidget(self.log)
            return
        self.log.show()

    def msg(self, msg):
        txt = self.log.toPlainText()
        txt += msg + '\n'
        self.log.setPlainText(txt)

    @lockme
    def _jobs(self, tot, pid='Operation'):
        """Initialize a new progress bar for job `pid` having total steps `tot`."""
        wg = self.prog.get(pid)
        if wg:
            wg.pb.setRange(0, tot)
            if not self.isVisible():
                self.ch.emit()
            return

        wg = QtGui.QWidget(parent=self)
        pb = QtGui.QProgressBar(parent=wg)
        pb.setRange(0, tot)
        lbl = QtGui.QLabel(pid, parent=wg)
        btn = QtGui.QPushButton('X', parent=wg)
        wg._func_close = functools.partial(self.done, pid)
        btn.connect(btn, QtCore.SIGNAL('clicked()'), wg._func_close)

        lay = QtGui.QHBoxLayout()
        lay.addWidget(lbl)
        lay.addWidget(pb)
        lay.addWidget(btn)
        wg.setLayout(lay)
        wg.pb = pb
        self.mlay.addWidget(wg)
        self.prog[pid] = wg
        if not self.isVisible():
            self.ch.emit()

    def jobs(self, tot, pid='Operation'):
        """Thread-safe call for _jobs()"""
        self.emit(QtCore.SIGNAL('jobs(int,QString)'), tot, pid)

    def _job(self, step, pid='Operation', label=''):
        """Progress job `pid` to `step`, and display `label`. A negative step causes the bar to progress by 1."""
        wg = self.prog.get(pid, False)
        if not wg:
            logging.debug('LocalTasks.job: no job defined! %s', pid)
            return
        if step < 0:
            step = wg.pb.value() + 1
        print 'setting progress bar to',pid,step, wg.pb.value(), wg.pb.maximum()
        wg.pb.setValue(step)
        if label != '':
            self.msg(pid + ': ' + label)
        if step == wg.pb.maximum() and step != 0:
            self._done(pid)
        QtGui.qApp.processEvents()

    def job(self, step, pid='Operation', label=''):
        """Thread-safe call for _job()"""
        self.emit(QtCore.SIGNAL('job(int,QString,QString)'),
                  step, pid, label)

    @lockme
    def _done(self, pid='Operation'):
        """Complete job `pid`"""
        wg = self.prog.get(pid, False)
        if not wg:
            return False
        wg.hide()
        wg.close()
        del self.prog[pid]
        self.mlay.removeWidget(wg)
        del wg
        self.msg('Completed task: ' + str(pid))
        logging.debug('%s %s', 'LocalTasks.done', self.prog)
        self.ch.emit()
        return True

    def done(self, pid='Operation'):
        """Thread-safe call for _done()"""
        self.emit(QtCore.SIGNAL('sig_done(QString)'), pid)
        self.emit(QtCore.SIGNAL('sig_done()'))


class Tasks(QtGui.QTabWidget):
    user_show = False
    """Detect if the user asked to view this widget"""

    hide_signal = QtCore.pyqtSignal()
    show_signal = QtCore.pyqtSignal()

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        QtGui.QTabWidget.__init__(self)

        self.setWindowTitle(_('Pending Tasks'))

        self.progress = PendingTasks(parent=self)
        self.addTab(self.progress, _('Remote'))

        self.tasks = LocalTasks(parent=self)
        self.addTab(self.tasks, _('Local'))

        self.sync = SyncWidget(parent=self)
        self.addTab(self.sync, _('Storage'))

        self.tasks.ch.connect(self.hide_show)
        self.progress.ch.connect(self.hide_show)
        self.sync.ch.connect(self.hide_show)

    def removeStorageAndRemoteTabs(self):
        self.removeTab(2)
        self.removeTab(0)

    def set_server(self, server):
        server = server.copy()
        server.connect()
        self.progress.set_server(server)
        self.sync.set_server(server)

    def update_active(self):
        """Switch the active tab"""

        browser_mode = self.count() == 1

        if len(self.progress):
            self.setCurrentIndex(0)
        elif len(self.tasks):
            print 'switch tab to local tasks', self.tasks.prog
            self.setCurrentIndex(1)
        elif len(self.sync) and not browser_mode:
            self.setCurrentIndex(2)
        else:
            return False
        return True

    def hide_show(self):
        """Decide if to automatically hide or show this window"""
        if self.update_active() or self.user_show:
            self.show()
            self.show_signal.emit()
        else:
            self.hide()
            self.hide_signal.emit()

    def hideEvent(self, e):
        self.user_show = False
        return QtGui.QWidget.hideEvent(self, e)

    def closeEvent(self, e):
        self.user_show = False
        self.hide()
        return None
