#!/usr/bin/python
# -*- coding: utf-8 -*-
from threading import Lock
from traceback import format_exc

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.csutil import unlockme

from .. import widgets, _
from ..live import registry

from .messages import StartedFinishedNotification, initial_sample_dimension, ValidationDialog

from PyQt4 import QtGui, QtCore
qm = QtGui.QMessageBox


class Controls(QtGui.QToolBar):

    """Start/stop toolbar"""
    mute = False
    motor = False
    coolAct = False
    isRunning = None
    """Local running status"""
    paused = False
    """Do not update actions"""
    _lock = False
    """Multithreading lock"""
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    closingTest_kid = False
    stop_mode = True
    stop_message = ''
    uid = None

    def __init__(self, remote, parent=None):
        QtGui.QToolBar.__init__(self, parent)
        self._lock = Lock()
        self.remote = remote
        logging.debug('Controls: init')
        self.ended_set = set()
        self.stopped_set = set()
        self.start_stop_notification = StartedFinishedNotification(self, self.started)
        self.server = remote.parent()
        self.startAct = self.addAction('Start', self.start)
        self.stopAct = self.addAction('Stop', self.stop)
        self.name = self.remote['devpath'].lower()

        if self.name != 'kiln':
            self.coolAct = self.addAction('Cool', self.stop_kiln)

        logging.debug('Controls: ', self.name)
        if self.name == 'post':
            self.addAction('Machine Database', parent.showIDB)
            self.addAction('Test File', parent.openFile)
            self.addAction('Misura3 Database', parent.showDB3)
        self.isRunning = self.server['isRunning']
        self.updateActions()
        logging.debug('Controls end init')
        self.stopped.connect(self.hide_prog)
        self.started.connect(self.hide_prog)
        self.connect(self, QtCore.SIGNAL('aboutToShow()'), self.updateActions)
        self.connect(
            self, QtCore.SIGNAL('warning(QString,QString)'), self.warning)
        self.closingTest_kid = self.remote.gete('closingTest')['kid']
        registry.system_kids.add(self.closingTest_kid)
        registry.system_kid_changed.connect(self.system_kid_slot)

    @unlockme
    def system_kid_slot(self, kid):
        """Slot processing system_kid_changed signals from KidRegistry.
        Calls updateActions if /isRunning is received."""
        logging.debug('system_kid_slot: received', kid)
        if not self._lock.acquire(False):
            logging.debug(
                "Controls.system_kid_slot: Impossible to acquire lock")
            return
        if kid == '/isRunning':
            self.updateActions()
        elif kid == self.closingTest_kid:
            uid = self.remote.measure['uid']
            if not self.uid:
                self.uid = uid
                return
            self.uid = uid
            if uid in self.ended_set:
                logging.info('End of test already notified')
                return
            if self.remote['closingTest'] != 0:
                self.closingTest = self.remote['closingTest']
                logging.debug(
                    'Waiting closingTest... ', self.remote['closingTest'])
                return

            if self.server['isRunning']:
                logging.error('Remote isRunning still!')
                return
            endStatus = self.remote.measure['endStatus']
            self.stopped.emit()
            self.emit(QtCore.SIGNAL('warning(QString,QString)'),
                      _('Measurement stopped and saved'),
                      _('Current measurement was stopped and its data has been saved. \n') + endStatus)
            self.ended_set.add(uid)
            self.isRunning = False

    @property
    def tasks(self):
        """Shortcut to pending tasks dialog"""
        return registry.tasks

    def updateActions(self):
        """Update status visualization and notify third-party changes"""
        if self.paused:
            return self.isRunning
        if self.parent().fixedDoc:
            return False
        # Always reconnect in case it is called in a different thread
        remote_server = self.server.copy()
        remote_server.connect()
        remote_is_running = bool(remote_server['isRunning'])

        self.stopAct.setEnabled(remote_is_running)

        if self.coolAct:
            self.coolAct.setEnabled(remote_is_running)

        self.startAct.setEnabled(remote_is_running ^ 1)
        uid = self.remote.measure['uid']
        if uid in self.ended_set:
            self.isRunning=remote_is_running
            return remote_is_running

        self.start_stop_notification.show(self.isRunning, remote_is_running, uid)

        # Locally remember remote_is_running status
        self.isRunning = remote_is_running
        return remote_is_running




    def enterEvent(self, ev):
        self.updateActions()
        return

    def _async(self, method, *a, **k):
        """Execute `method` in global thread pool, passing `*a`,`**k` arguments."""
        r = widgets.RunMethod(method, *a, **k)
        r.pid = self.async_pid
        QtCore.QThreadPool.globalInstance().start(r)
        return True

    def _sync(self, method, *a, **k):
        """Synchronously execute `method`,passing `*a`,`**k` arguments."""
        method(*a, **k)
        return True

    def warning(self, title, msg=False):
        """Display a warning message box and update actions"""
        if not self.mute:
            if not msg:
                msg = title
            qm.warning(self, title, msg)
        self.updateActions()

    msg = ''

    def show_prog(self, msg):
        self.msg = msg
        self.tasks.jobs(0, msg)
        self.tasks.setFocus()

    def hide_prog(self):
        self.tasks.done(self.msg)

    def _start(self):
        # Renovate the connection: we are in a sep thread!
        self.paused = True
        rem = self.remote.copy()
        rem.connect()
        try:
            msg = rem.start_acquisition()
            self.started.emit()
        except:
            msg = format_exc()
            logging.debug(msg)
        self.paused = False
        self.started.emit()
        if not self.mute:
            self.emit(QtCore.SIGNAL('warning(QString,QString)'),
                      _('Start Acquisition'),
                      _('Result: ') + msg)

    def start(self):
        self.async_pid = "Starting"
        self.tasks.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Preferred)

        self.mainWin = self.parent()
        self.mDock = self.mainWin.measureDock
        self.measureTab = self.mDock.widget()
        self.measureTab.setCurrentIndex(0)

        self.measureTab.checkCurve()
        if not self.validate():
            return False
        if self.updateActions():
            self.warning(
                _('Already running'), _('Acquisition is already running. Nothing to do.'))
            return False
        
        confirmation = ValidationDialog(self.server, self).exec_()
        if not confirmation:
            return
        
        
        self.isRunning = True
        self._async(self._start)
        self.show_prog(_("Starting new test"))
        return True

    def _stop(self):
        self.paused = True
        rem = self.remote.copy()
        rem.connect()
        try:
            self.stop_message = rem.stop_acquisition(True)
        except:
            self.stop_message = format_exc()
        self.paused = False

    def stop(self):
        self.async_pid = "Stopping"
        self.tasks.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Preferred)

        if not self.updateActions():
            self.warning(
                _('Already stopped'), _('No acquisition is running. Nothing to do.'))
            return
        if not self.mute:
            btn = qm.question(self, _('Warning'),
                              _('Do you want to stop this measurement?'),
                              qm.No | qm.Yes, qm.No)
            if btn == qm.No:
                qm.information(self,
                               _('Nothing done.'),
                               _('Action aborted. The measurement maybe still running.'))
                return False

        self.show_prog("Stopping current test")

        self.isRunning = False
        self._async(self._stop)

    def stop_kiln(self):
        """Stop thermal cycle without interrupting the acquisition"""
        # Disable auto-stop on thermal cycle end
        self.remote.measure.setFlags('onKilnStopped', {'enabled': False})
        self.server.kiln['analysis'] = False
        dur = self.remote.measure['duration']
        elp = self.remote.measure['elapsed']
        msg = _('Thermal cycle interrupted')
        if dur > 0:
            rem = (dur * 60 - elp) / 60.
            qm.information(self, msg,
                           _('Thermal cycle interrupted.\nThe test will finish in {:.1f} minutes.').format(rem))
        else:
            self.warning(msg,
                         _('Thermal cycle interrupted, but no test termination is set: acquisition  may continue indefinitely. \nManually interrupt or set a maximum test duration.'))

    def new(self):
        self.parent().init_instrument()

    def validate(self):
        """Show a confirmation dialog immediately before starting a new test"""
        return initial_sample_dimension(self.remote, parent=self)




class MotionControls(QtGui.QToolBar):

    """Motion toolbar"""
    mute = False
    motor = False
    # cycleNotSaved=False

    def __init__(self, remote, parent=None):
        QtGui.QToolBar.__init__(self, parent)
        self.remote = remote
        self.server = remote.parent()

        if self.server.kiln['motorStatus'] >= 0:
            self.kmotor = widgets.build(
                self.server, self.server.kiln, self.server.kiln.gete('motorStatus'))
            self.kmotor.label_widget.setText('Furnace:')
            self.kmotor.lay.insertWidget(0, self.kmotor.label_widget)
            self.addWidget(self.kmotor)

        paths = {}
        # Collect all focus paths
        for pic, win in self.parent().cameras.itervalues():
            logging.debug(pic)
            logging.debug(pic.remote)
            logging.debug(pic.remote.encoder)
            logging.debug(pic.remote.encoder.focus)

            obj = pic.remote.encoder.focus.role2dev('motor')
            if not obj:
                continue
            paths[obj['fullpath']] = obj
        for obj in paths.itervalues():
            self.add_focus(obj)

    def add_focus(self, obj):
        #       slider=widgets.MotorSlider(self.server,obj,self.parent())
        slider = widgets.build(self.server, obj, obj.gete('goingTo'))
        slider.lay.insertWidget(0, slider.label_widget)
        slider.label_widget.setText('    Focus:')
        self.addWidget(slider)
