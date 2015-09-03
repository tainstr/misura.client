#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools
from time import sleep, time
import threading
from traceback import format_exc
import os
import sys
import tables

from misura.canon.logger import Log as logging
from misura.canon import csutil

from .. import _
from ..live import registry
from .. import network
from ..network import TransferThread
from .. import widgets, beholder
from .. import fileui, filedata
from ..misura3 import m3db
from .. import connection
from ..clientconf import confdb, settings
from ..confwidget import RecentWidget
from .menubar import MenuBar
from .selector import InstrumentSelector
from .measureinfo import MeasureInfo
from .controls import Controls, MotionControls
from .delay import DelayedStart
from .results import Results

from .. import graphics
from ..database import UploadThread
from ..filedata import RemoteFileProxy

from PyQt4 import QtGui, QtCore

subWinFlags = QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowMinMaxButtonsHint

roles = {'motorBase': 'Base Position', 'motorHeight': 'Height Position',
         'motorRight': 'Right Position', 'motorLeft': 'Left Position',
         'focus': 'Focus adjust', 'motor': 'Position', 'camera': 'Main',
         'cameraBase': 'Base', 'cameraHeight': 'Height', 'cameraRight': 'Right',
         'cameraLeft': 'Left', 'force': 'Weight',
         'angleHeight': 'Height Inclination', 'angleBase': 'Base Inclination',
         'angleRight': 'Right Inclination', 'angleLeft': 'LeftInclination'}


def check_time_delta(server):
    """Detect time delta, warn the user, restart if delta is approved."""
    if server['isRunning'] or server['runningInstrument']:
        logging.debug('running analysis: do not check time delta')
        return True
    t = time()
    s = server.time()
    dt = time() - t
    delta = int((t - s) + (dt / 3.))
    if delta < 10:
        logging.debug('Time delta is not significant',delta)
        return True
    pre = server['timeDelta']
    if pre:
        logging.debug('Time delta already set: %', server['timeDelta'])
    btn = QtGui.QMessageBox.warning(self,'Hardware clock error',
                      'Instrument time is different from your current time (delta: {}s).\n Apply difference and restart?'.format(delta))
    if btn != QtGui.QMessageBox.Ok:
        logging.debug('Delta correction aborted')
        return True
    #TODO: warn the user about time delta
    logging.info('Apply time delta to server',delta)
    server['timeDelta'] = delta
    r = server.restart()
    QtGui.QMessageBox.information(self,'Restarting','Instrument is restarting: ' + r)
    return False

class MainWindow(QtGui.QMainWindow):

    """Generalized Acquisition Interface"""
    remote = None
    doc = False
    uid = False


    @property
    def tasks(self):
        if getattr(self, '_tasks', False):
            return self._tasks

        # DEBUG needed for UT
        if not registry.tasks:
            logging.debug('Preparing registry.tasks object')
            registry.set_manager(network.manager)
            if self.server and not self.fixedDoc:
                registry.progress.set_server(self.server)

        return registry.tasks

    def __init__(self, doc=False, parent=None):
        super(MainWindow, self).__init__(parent)
        self._lock = threading.Lock()
        self.saved_set = set()
        self.cameras = {}
        self.toolbars = []
        self.fixedDoc = doc
        self.server = False
        self.area = QtGui.QMdiArea()
        self.setCentralWidget(self.area)
        self.setMinimumSize(800, 600)
        self.setWindowTitle(_('Misura Live'))
        self.myMenuBar = MenuBar(parent=self)
        self.setMenuWidget(self.myMenuBar)
        self.add_server_selector()
        self.reset_proxy_timer = QtCore.QTimer(parent=self)
        self.reset_proxy_timer.setSingleShot(True)
        self.reset_proxy_timer.setInterval(500)
        self.connect(self.reset_proxy_timer, QtCore.SIGNAL(
            'timeout()'), self._resetFileProxy)
        self.reset_file_proxy_timer = QtCore.QTimer()

    def add_server_selector(self):
        """Server selector dock widget"""
        self.serverDock = QtGui.QDockWidget(self.centralWidget())
#       self.serverSelector=connection.ServerSelector(self.serverDock)
        self.serverSelector = RecentWidget(confdb, 'server', self.serverDock)
        self.connect(
            self.serverSelector, self.serverSelector.sig_select, self.set_addr)
        self.serverDock.setWindowTitle(self.serverSelector.label)
        self.serverDock.setWidget(self.serverSelector)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.serverDock)

    def rem(self, d, w=False):
        """Removes a dock widget by name"""
        d = getattr(self, d, False)
        if not d:
            return
        self.removeDockWidget(d)
        d.deleteLater()
        if not w:
            return
        w = getattr(self, w, False)
        if w:
            w.deleteLater()

    def set_addr(self, addr):
        logging.debug('MainWindow.set_addr %s', addr)
        user, password = confdb.getUserPassword(addr)
        self.login_window = connection.LoginWindow(
            addr, user, password, globalconn=False)
        self.login_window.login_failed.connect(
            self.retry_login, QtCore.Qt.QueuedConnection)
        self.login_window.login_succeeded.connect(
            self.succeed_login, QtCore.Qt.QueuedConnection)
        r = widgets.RunMethod(self.login_window.tryLogin, user, password, addr)
        r.pid = 'Connecting to ' + addr
        QtCore.QThreadPool.globalInstance().start(r)

    def retry_login(self):
        """Called when set_addr fails"""
        self.login_window.exec_()
        if not self.login_window.obj:
            self.login_window.close()

    def succeed_login(self, rem=False):
        """Called on new address successfully connected"""
        if not rem:
            rem = self.login_window.obj
        network.manager.set_remote(rem)
        registry.set_manager(network.manager)
        self.setServer(rem)

    def closeEvent(self, ev):
        if not self.fixedDoc:
            registry.toggle_run(False)
            self.tasks.close()
        super(MainWindow, self).closeEvent(ev)
    _blockResetFileProxy = False


    def setServer(self, server=False):
        self._blockResetFileProxy = True
        logging.debug('%s %s', 'Setting server to', server)
        self.server = server
        if not server:
            network.manager.remote.connect()
            self.server = network.manager.remote
        if not check_time_delta(self.server):
            return False
        registry.toggle_run(True)
        self.serverDock.hide()
        self.myMenuBar.close()
        del self.myMenuBar
        self.myMenuBar = MenuBar(server=self.server, parent=self)
        self.rem('logDock')
        self.logDock = QtGui.QDockWidget(self.centralWidget())
        self.logDock.setWindowTitle('Log Messages')
        if self.fixedDoc:
            self.logDock.setWidget(
                fileui.OfflineLog(self.fixedDoc.proxy, self.logDock))
        else:
            self.logDock.setWidget(connection.LiveLog(self.logDock))
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.logDock)

        self.setMenuBar(self.myMenuBar)

        self.rem('instrumentDock')
        self.instrumentDock = QtGui.QDockWidget(self.centralWidget())
        self.instrumentSelector = InstrumentSelector(self, self.setInstrument)
        self.instrumentDock.setWidget(self.instrumentSelector)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.instrumentDock)
        logging.debug('%s', self.server.describe())
        ri = self.server['runningInstrument']  # currently running
        li = ri
        # compatibility with old tests
        if self.server.has_key('lastInstrument'):
            li = self.server['lastInstrument']  # configured, ready, finished
        if ri in ['None', '']:
            ri = li
        if ri not in ['None', '']:
            remote = getattr(self.server, ri)
            self.setInstrument(remote)
        if self.fixedDoc:
            return True
        # Automatically pop-up delayed start dialog
        if self.server['delayStart']:
            self.delayed_start()
        return True

    def add_measure(self):
        # MEASUREMENT INFO
        self.rem('measureDock', 'measureTab')
        self.measureDock = QtGui.QDockWidget(self.centralWidget())
        self.measureDock.setWindowTitle(' Test Configuration')
        self.measureTab = MeasureInfo(
            self.remote, self.fixedDoc, parent=self.measureDock)
        self.measureDock.setWidget(self.measureTab)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.measureDock)

    def add_snapshots(self):
        # SNAPSHOTS
        self.rem('snapshotsDock', 'snapshotsStrip')
        self.snapshotsDock = QtGui.QDockWidget(self.centralWidget())
        self.snapshotsDock.setWindowTitle('Snapshots')
        self.imageSlider = fileui.ImageSlider()
        self.snapshotsDock.setWidget(self.imageSlider)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.snapshotsDock)
        if self.name not in ['hsm', 'post', 'drop']:
            self.snapshotsDock.hide()

    def add_sumtab(self):
        # SUMMARY TREE - In lateral measureTab
        self.measureTab.results = Results(self, self.summaryPlot)
        self.navigator = self.measureTab.results.navigator
        self.measureTab.refreshSamples()

    def add_graph(self):
        # PLOT window
        w = getattr(self, 'summaryPlot', False)
        g = getattr(self, 'graphWin', False)
        if w:
            w.close()
            del w
        if g:
            self.graphWin.deleteLater()
            del self.graphWin
        self.summaryPlot = graphics.Plot()
        self.graphWin = self.centralWidget().addSubWindow(
            self.summaryPlot, subWinFlags)
        self.graphWin.setWindowTitle('Data Plot')
        self.graphWin.hide()

    def add_table(self):
            # Data Table (tabular view) window
        w = getattr(self, 'dataTable', False)
        if w:
            w.close()
            del w
            self.tableWin.deleteLater()
        self.dataTable = fileui.SummaryView(parent=self)
        self.tableWin = self.centralWidget().addSubWindow(
            self.dataTable, subWinFlags)
        self.tableWin.hide()

    def _init_instrument(self, soft=False):
        """Called in a different thread. Need to recreate connection."""
        r = self.remote.copy()
        r.connect()
        result = r.init_instrument(soft)


    def init_instrument(self, soft=False):
        # TODO: this scheme could be automated via a decorator: @thread
        logging.debug('%s', 'Calling init_instrument in QThreadPool')
        r = widgets.RunMethod(self._init_instrument, soft)
        r.pid = 'Instrument initialization '
        QtCore.QThreadPool.globalInstance().start(r)
        logging.debug('%s %s %s', 'active threads:', QtCore.QThreadPool.globalInstance(
        ).activeThreadCount(), QtCore.QThreadPool.globalInstance().maxThreadCount())

    def setInstrument(self, remote=False, server=False):
        if server is not False:
            self.setServer(server)
        if remote is False:
            remote = self.remote
        else:
            self.remote = remote
        self._blockResetFileProxy = True
        self.instrumentDock.hide()
        name = self.remote['devpath']
        self.name = name
        logging.debug('Setting remote %s %s %s', remote, self.remote, name)
        self.setWindowTitle('misura Acquisition: %s (%s)' %
                            (name, self.remote['comment']))
        pid = 'Instrument: ' + self.name
        self.tasks.jobs(11, pid)
        QtGui.qApp.processEvents()
        if not self.fixedDoc and not self.server['isRunning'] and self.name != self.server['lastInstrument']:
            logging.debug('Init instrument')
            if self.remote.init_instrument is not None:
                self.tasks.job(0, pid, 'Initializing instrument')
                QtGui.qApp.processEvents()
                # Async call of init_instrument
                # soft: only if not already initialized
                self.init_instrument(soft=True)
#               QtCore.QThreadPool.globalInstance().waitForDone()
                logging.debug('%s %s %s', 'active threads:', QtCore.QThreadPool.globalInstance(
                ).activeThreadCount(), QtCore.QThreadPool.globalInstance().maxThreadCount())
#               sleep(10)
#               self.remote.init_instrument()
        self.tasks.job(1, pid, 'Preparing menus')
        self.myMenuBar.close()
        self.myMenuBar = MenuBar(server=self.server, parent=self)
        self.setMenuWidget(self.myMenuBar)
        logging.debug('%s', 'Done menubar')

        # Close cameras
        for p, (pic, win) in self.cameras.iteritems():
            logging.debug('deleting cameras', p, pic, win)
            pic.close()
            win.hide()
            win.close()
            win.deleteLater()
        self.cameras = {}
        # Remove any remaining subwindow
        self.centralWidget().closeAllSubWindows()

        self.tasks.job(1, pid, 'Controls')
        for tb in self.toolbars:
            self.removeToolBar(tb)
            tb.close()
            del tb
        self.toolbars = []
        logging.debug('%s', 'Cleaned toolbars')
        self.controls = Controls(self.remote, parent=self)
        logging.debug('%s', 'Created controls')
        self.controls.stopped_nosave.connect(self.stopped_nosave)
        self.controls.stopped.connect(self.stopped)
        self.controls.started.connect(self.resetFileProxy)
        self.controls.mute = bool(self.fixedDoc)
        self.addToolBar(self.controls)
        self.toolbars.append(self.controls)
        logging.debug('%s', 'Done controls')
        self.tasks.job(-1, pid, 'Status panel')

        self.logDock.hide()
        self.add_measure()

        self.tasks.job(-1, pid, 'Frames')
        self.add_snapshots()

        self.tasks.job(-1, pid, 'Graph')
        self.add_graph()

        self.tasks.job(-1, pid, 'Data tree')
        self.add_sumtab()

        self.tasks.job(-1, pid, 'Data Table')
        self.add_table()

        # Update Menu
        self.tasks.job(-1, pid, 'Filling menus')
        logging.debug('%s %s', 'MENUBAR SET INSTRUMENT', remote)
        self.myMenuBar.setInstrument(remote, server=self.server)
        self.myMenuBar.show()

        # Populate Cameras
        self.tasks.job(-1, pid, 'Show cameras')
        paths = self.remote['devices']
        logging.debug('%s %s', 'setInstrument PATHS:', paths)

        for path in paths:
            lst = self.server.searchPath(path[1])
            if not lst:
                continue
            obj = self.server.toPath(lst)
            if obj is None:
                continue
#           role=obj['role'][self.name]
            role = 'NoRole'
            if 'Camera' in obj['mro']:
                an = name.lower()
                if an == 'post':
                    an = 'post'
                if role == 'NoRole':
                    role = 'Camera'
                self.addCamera(obj, role, an)

        # Add motion controls toolbar
        if not self.fixedDoc:
            self.mcontrols = MotionControls(self.remote, parent=self)
            self.addToolBar(QtCore.Qt.BottomToolBarArea, self.mcontrols)
            self.toolbars.append(self.mcontrols)

        # Connect to "id" property
        self.tasks.job(-1, pid, 'Document')
        self.idobj = widgets.ActiveObject(
            self.server, self.remote.measure, self.remote.measure.gete('id'), parent=self)
        self.connect(self.idobj, QtCore.SIGNAL(
            'changed()'), self.resetFileProxy, QtCore.Qt.QueuedConnection)
        # Reset decoder and plot
        self.resetFileProxy()
        for obj1 in [self.dataTable, self.navigator, self.summaryPlot]:
            for obj2 in [self.dataTable, self.navigator, self.summaryPlot]:
                if obj1 == obj2:
                    continue
                p = functools.partial(obj2.hide_show, emit=False)
                self.connect(
                    obj1, QtCore.SIGNAL('hide_show_col(QString,int)'), p)
        self.tasks.done(pid)

    def addCamera(self, obj, role='', analyzer='hsm'):
        pic = beholder.ViewerControl(obj, self.server, parent=self)
        pic.role = role
        win = self.centralWidget().addSubWindow(pic, subWinFlags)
        win.setWindowTitle('%s (%s)' % (roles.get(role, role), obj['name']))
        win.resize(640, 480)
        if not self.fixedDoc:
            win.show()
        else:
            win.hide()
#       self.connect(pic, QtCore.SIGNAL('updatedROI()'), win.repaint)
        self.cameras[obj['fullpath']] = (pic, win)


#   @csutil.lockme
    def set_doc(self, doc=False):
        if doc is False:
            doc = filedata.MisuraDocument(root=self.server)
        doc.up = True
        pid = 'Data display'
        self.tasks.jobs(10, pid)
        self.doc = doc
        self.tasks.job(-1, pid, 'Setting document in live registry')
        registry.set_doc(doc)

        logging.debug('%s', 'imageSlider')
        self.tasks.job(-1, pid, 'Sync snapshots with document')
        self.imageSlider.set_doc(doc)

        logging.debug('%s', 'summaryPlot')
        self.tasks.job(-1, pid, 'Sync graph with document')
        self.summaryPlot.set_doc(doc)

        logging.debug('%s', 'navigator')
        self.tasks.job(-1, pid, 'Sync document tree')
        self.navigator.set_doc(doc)

        self.measureTab.set_doc(doc)

        logging.debug('%s', 'dataTable')
        self.tasks.job(-1, pid, 'Sync data table')
        self.dataTable.set_doc(doc)
        logging.debug('%s', 'connect')
        self.connect(self.imageSlider, QtCore.SIGNAL(
            'set_time(float)'), self.set_slider_position)
        self.connect(self.imageSlider, QtCore.SIGNAL(
            'sliderReleased()'), self.slider_released)

        self.connect(self.imageSlider, QtCore.SIGNAL(
            'set_time(float)'), self.navigator.set_time)
        self.connect(self.summaryPlot, QtCore.SIGNAL(
            'move_line(float)'), self.imageSlider.set_time)
        self.tasks.done(pid)

    max_retry = 10

    def set_slider_position(self, position):
        self.current_slider_position = position

    def slider_released(self):
        self.summaryPlot.set_time(self.current_slider_position)

    def resetFileProxyLater(self, retry, recursion):
        self.reset_file_proxy_timer.singleShot(1000, lambda : self._resetFileProxy(retry, recursion))

    def release_lock(self):
        try:
            self._lock.release()
        except:
            pass

    def _resetFileProxy(self, retry=0, recursion=0):
        """Resets acquired data widgets"""
        if self._blockResetFileProxy:
            self.release_lock()
            return False

        if self.doc:
            self.doc.close()
            self.doc = False

        doc = False
        fid = False

        if self.fixedDoc is not False:
            fid = 'fixedDoc'
            doc = self.fixedDoc
        elif self.server['initTest'] or self.server['closingTest']:
            self.tasks.jobs(0, 'Test initialization')
            if recursion == 0:
                self.tasks.setFocus()
            logging.debug('%s', 'Waiting for initialization to complete...')
            self.resetFileProxyLater(0, recursion + 1)
            return
        else:
            if not self.server['isRunning']:
                retry = self.max_retry
            self.tasks.jobs(self.max_retry, 'Waiting for data')
            self.tasks.done('Test initialization')
            self.tasks.job(retry, 'Waiting for data')
            if retry < self.max_retry:
                self.resetFileProxyLater(retry + 1, recursion + 1)
                return
            if retry > self.max_retry:
                self.tasks.done('Waiting for data')
                QtGui.QMessageBox.critical(self, _('Impossible to retrieve the ongoing test data'),
                                           _("""A communication error with the instrument does not allow to retrieve the ongoing test data.
                        Please restart the client and/or stop the test."""))
                self.release_lock()
                return False
            fid = self.remote.measure['uid']
            if fid == '':
                logging.debug('%s %s', 'no active test', fid)
                self.tasks.done('Waiting for data')
                self.release_lock()
                return False
            logging.debug('%s %s', 'resetFileProxy to live ', fid)
            self.server.connect()
            live_uid = self.server.storage.test.live.get_uid()
            if not live_uid:
                logging.debug('No live_uid returned')
                self.release_lock()
                return False
            live = getattr(self.server.storage.test, live_uid)
            if not live.has_node('/conf'):
                live.load_conf()
            if not live.has_node('/conf'):
                logging.debug(
                    '%s', 'Conf node not found: acquisition has not been initialized.')
                self.tasks.job(0, 'Waiting for data',
                               'Conf node not found: acquisition has not been initialized.')
                self.tasks.done('Waiting for data')
                self.release_lock()
                return False
            if fid == self.uid:
                logging.debug(
                    '%s', 'Measure id is still the same. Aborting resetFileProxy.')
                self.tasks.job(0, 'Waiting for data',
                               'Measure id is still the same. Aborting resetFileProxy.')
                self.tasks.done('Waiting for data')
                self.release_lock()
                return False
            try:
                #               live.reopen() # does not work when file grows...
                fp = RemoteFileProxy(live, conf=self.server, live=True)
                logging.debug('%s', fp.header())
                doc = filedata.MisuraDocument(proxy=fp)
                # Remember as the current uid
                self.uid = fid
            except:
                logging.debug('RESETFILEPROXY error')
                logging.debug(format_exc())
                doc = False
                self.resetFileProxyLater(retry + 1, recursion + 1)
                return
        self.tasks.done('Waiting for data')
        logging.debug(
            '%s %s %s %s', 'RESETFILEPROXY', doc.filename, doc.data.keys(), doc.up)
        self.set_doc(doc)
        self._finishFileProxy()


    def resetFileProxy(self, *a, **k):
        """Locked version of resetFileProxy"""
        if not self._lock.acquire(False):
            logging.debug('ANOTHER RESETFILEPROXY IS RUNNING!')
            return False
        self._blockResetFileProxy = False
        logging.debug('MainWindow.resetFileProxy: Stopping registry')
        registry.toggle_run(False)

        self._resetFileProxy(*a, **k)

    @csutil.unlockme
    def _finishFileProxy(self):
        logging.debug('%s', 'MainWindow.resetFileProxy: Restarting registry')
        registry.toggle_run(True)
        self.tasks.done('Waiting for data')
        self.tasks.hide()

    ###########
    # ## Start/Stop utilities
    ###########

    def delayed_start(self):
        """Configure delayed start"""
        # TODO: disable the menu action!
        if self.server['isRunning']:
            QtGui.QMessageBox.warning(
                self, "Already running", "Cannot set a delayed start. \nInstrument is already running.")
            return False
        self.delayed = DelayedStart(self.server)
        self.delayed.show()

    def stopped_nosave(self):
        """Reset the instrument, completely discarding acquired data and remote file proxy"""
        logging.debug('%s', "STOPPED_NOSAVE")
        # TODO: reset ops should be performed server-side
        self.remote.measure['uid'] = ''
        if self.doc:
            self.doc.close()
        self.set_doc(False)
        self.resetFileProxy(retry=10)

    def stopped(self):
        """Offer option to download the remote file"""
        # HTTPS data url
        uid = self.remote.measure['uid']
        if uid in self.saved_set:
            logging.debug('UID already saved!')
            return
        self.saved_set.add(uid)
        dbpath = confdb['database']
        if self.doc:
            self.doc.close()
        self.set_doc(False)
        self.resetFileProxy(retry=10)
        registry.toggle_run(False)
        # NO db: ask to specify custom location
        if not os.path.exists(dbpath):
            logging.debug('%s %s', 'DATABASE PATH DOES NOT EXIST', dbpath)
            dbpath = False
            d = settings.value('/FileSaveToDir', os.path.expanduser('~'))
            path = os.path.join(str(d), self.remote.measure['name'] + '.h5')
            outfile = QtGui.QFileDialog.getSaveFileName(
                self,   _("Download finished test as"),
                path,
                filter="Misura (*.h5)")
            outfile = str(outfile)
            settings.setValue('/FileSaveToDir', os.path.dirname(outfile))
            if not len(outfile):
                registry.toggle_run(True)
                return False
            auto = True
        else:
            auto = confdb['autodownload']
            outfile = False
        # Ask if it's not automatic
        if not auto:
            auto = QtGui.QMessageBox.question(self, _("Download finished test?"),
                                              _("Would you like to save the finished test?"))
            if auto != QtGui.QMessageBox.Ok:
                registry.toggle_run(True)
                return False
        # TODO: Must wait that current file is closed!!!
        # Must download
        sy = TransferThread(
            outfile=outfile, uid=uid, server=self.server, dbpath=dbpath)
        sy.set_tasks(self.tasks)
        sy.start()
        # Keep a reference
        self._download_thread = sy
        registry.toggle_run(True)
        return True

    ###########
    # ## Post-analysis
    ###########
    def showIDB(self):
        """Shows remote database selection window."""
        self.idb = DatabaseWidget(self.server.storage, self)
        win = self.centralWidget().addSubWindow(self.idb)
        self.connect(
            self.idb, QtCore.SIGNAL('selectedUid(QString)'), self.post_uid)
        win.show()

    def showDB3(self):
        """Shows selection windows for db3."""
        self.db3Dia = m3db.TestDialog(self)
        self.db3Dia.importAllFields = True
        win = self.centralWidget().addSubWindow(self.db3Dia)
        win.show()
        self.connect(
            self.db3Dia, QtCore.SIGNAL('imported(QString)'), self.post_file)

    def openFile(self):
        """Selects misura HDF file for post-analysis"""
        path = QtGui.QFileDialog.getOpenFileName(
            self, "Select misura File", "C:\\")
        if not path:
            return
        self.post_file(path)

    def post_file(self, filename):
        """Slot called when a misura file is opened for post-analysis."""
        # TODO: migrate to the new SharedFile interface
        filename = str(filename)
        f = tables.openFile(filename, 'r')
        uid = str(f.root.summary.attrs.uid)
        f.close()
        r = self.post_uid(uid)
        if not r:
            upthread = UploadThread(self.server.storage, filename, parent=self)
            upthread.show()
            upthread.start()
            self.reinit_post = functools.partial(self.post_uid, filename)
            self.connect(upthread, QtCore.SIGNAL('ok()'), self.reinit_post)
            return False

    def post_uid(self, uid):
        uid = str(uid)
        r = self.server.storage.searchUID(uid)
        logging.debug('%s %s', 'SEARCH UID', r)
        if not r:
            return False
        self.remote.init_uid(uid)
        # Attiva lo streaming se è spento
        for cam, win in self.cameras.itervalues():
            cam.toggle(1)
        return True
