#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools
from time import time, sleep
import threading
from traceback import format_exc
import os
import tables

from veusz import utils as vutils

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon import csutil
from misura.client import configure_logger

from .. import _
from ..live import registry
from .. import network
from ..network import TransferThread
from .. import widgets, beholder
from .. import fileui, filedata
from .. import misura3
from .. import connection
from ..livelog import LiveLog
from .. import iutils
from .. import parameters
from ..clientconf import confdb
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
from . import windows

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
        logging.debug('Time delta is not significant', delta)
        return True
    pre = server['timeDelta']
    if pre:
        logging.debug('Time delta already set:', server['timeDelta'])
    btn = QtGui.QMessageBox.warning(None, _('Hardware clock error'),
                      _('Instrument time is different from your current time (delta: {}s).\n Apply difference and restart?').format(delta),
                      QtGui.QMessageBox.Cancel|QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
    if btn != QtGui.QMessageBox.Ok:
        logging.debug('Delta correction aborted')
        return True
    # TODO: warn the user about time delta
    logging.info('Apply time delta to server', delta)
    server['timeDelta'] = delta
    r = server.restart()
    QtGui.QMessageBox.information(None, 'Restarting', 'Instrument is restarting: ' + r)
    return False

class MainWindow(QtGui.QMainWindow):

    """Generalized Acquisition Interface"""
    remote = None
    doc = False
    uid = False
    name = 'MainWindow'
    reset_instrument = QtCore.pyqtSignal()
    """Connected to setInstrument"""
    server = False
    remote = False
    myMenuBar = False
    plotboardDock = False

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

    def instrument_pid(self):
        return 'Instrument: ' + self.name


    def __init__(self, doc=False, parent=None):
        super(MainWindow, self).__init__(parent)
        configure_logger('acquisition.log')
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
        self.add_menubar()
        
        self.add_statusbar()
        self.add_server_selector()

        self.reset_file_proxy_timer = QtCore.QTimer()
        self.reset_instrument_timer = QtCore.QTimer()
        self.reset_instrument.connect(self.setInstrument)
        self.tray_icon = QtGui.QSystemTrayIcon(self)
        self.connect(self.tray_icon, QtCore.SIGNAL('messageClicked()'), self.focus_logging)
        self.setWindowIcon(QtGui.QIcon(os.path.join(parameters.pathArt, 'icon.svg')))
        if not self.fixedDoc and confdb['autoConnect'] and len(confdb['recent_server']) > 1:
            self.set_addr(confdb['recent_server'][-1][0])
        self.showMaximized()
        
    
    def add_menubar(self, setInstrument=True):
        if self.myMenuBar:
            self.myMenuBar.clear_windows()
            self.myMenuBar.close()
            del self.myMenuBar
        self.myMenuBar = MenuBar(server=self.server, parent=self)
        if self.remote and self.server and setInstrument:
            self.myMenuBar.setInstrument(self.remote, self.server)  
        self.setMenuBar(self.myMenuBar)
        self.myMenuBar.quitClient.connect(self.close)
        
        
    def add_statusbar(self):
        """Add statusBar widgets"""
        statusbar = self.statusbar = QtGui.QStatusBar(self)
        self.setStatusBar(statusbar)
        self.updateStatusbar(_('Ready'))

        # a label for the picker readout
        self.pickerlabel = QtGui.QLabel(statusbar)
        self._setPickerFont(self.pickerlabel)
        statusbar.addPermanentWidget(self.pickerlabel)
        self.pickerlabel.hide()

        # plot queue - how many plots are currently being drawn
        self.plotqueuecount = 0
        
        self.plotqueuelabel = QtGui.QLabel()
        self.plotqueuelabel.setToolTip(_("Number of rendering jobs remaining"))
        statusbar.addWidget(self.plotqueuelabel)
        self.plotqueuelabel.show()

        # a label for the cursor position readout
        self.widgetnamelabel = QtGui.QLabel(statusbar)
        statusbar.addPermanentWidget(self.widgetnamelabel)
        self.widgetnamelabel.show()
        
        # a label for the cursor position readout
        self.axisvalueslabel = QtGui.QLabel(statusbar)
        statusbar.addPermanentWidget(self.axisvalueslabel)
        self.axisvalueslabel.show()

        # a label for the page number readout
        self.pagelabel = QtGui.QLabel(statusbar)
        statusbar.addPermanentWidget(self.pagelabel)
        self.pagelabel.show()
        
    def connect_statusbar(self):
        self.summaryPlot.plot.sigQueueChange.connect(self.plotQueueChanged)
        self.summaryPlot.plot.sigPointPicked.connect(self.slotUpdatePickerLabel)
        self.summaryPlot.plot.sigAxisValuesFromMouse.connect(self.slotUpdateAxisValues)
        self.summaryPlot.plot.sigNearestWidget.connect(self.slotUpdateNearWidget)
        self.summaryPlot.plot.sigUpdatePage.connect(self.slotUpdatePage)
        
    def slotUpdateNearWidget(self, widget):
        txt = widget.path
        for s in ('notes', 'key', 'label'):
            if s in widget.settings:
                txt = widget.settings.get(s).val
                break
        self.widgetnamelabel.setText(txt)
        
    def slotUpdatePickerLabel(self, info):
        """Display the picked point"""
        #TODO: disentangle from Veusz code and import from there
        xv, yv = info.coords
        xn, yn = info.labels
        xt, yt = info.displaytype
        ix = str(info.index)
        if ix:
            ix = '[' + ix + ']'

        # format values for display
        def fmt(val, dtype):
            if dtype == 'date':
                return vutils.dateFloatToString(val)
            elif dtype == 'numeric':
                return '%0.5g' % val
            elif dtype == 'text':
                return val
            else:
                raise RuntimeError

        xtext = fmt(xv, xt)
        ytext = fmt(yv, yt)

        t = '%s: %s%s = %s, %s%s = %s' % (
            info.widget.name, xn, ix, xtext, yn, ix, ytext)
        self.pickerlabel.setText(t)
        
    def slotUpdateAxisValues(self, values):
        """Update the position where the mouse is relative to the axes."""
        #TODO: disentangle from Veusz code and import from there
        if values:
            # construct comma separated text representing axis values
            valitems = [
                '%s=%#.4g' % (name, values[name])
                for name in sorted(values) ]
            self.axisvalueslabel.setText(', '.join(valitems))
        else:
            self.axisvalueslabel.setText(_('No position'))
            
    def slotUpdatePage(self, number):
        """Update page number when the plot window says so."""

        np = self.doc.getNumberPages()
        if np == 0:
            self.pagelabel.setText(_("No pages"))
        else:
            self.pagelabel.setText(_("Page %i/%i") % (number+1, np))
            
    def plotQueueChanged(self, incr):
        self.plotqueuecount += incr
        text = u'•' * self.plotqueuecount
        self.plotqueuelabel.setText(text)
            
    def updateStatusbar(self, text):
        '''Display text for a set period.'''
        self.statusBar().showMessage(text, 2000)
        
    def _setPickerFont(self, label):
        f = label.font()
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() * 1.2)
        label.setFont(f)

    def notify(self, level, msg):
        if level<confdb['lognotify']:
            return False
        self.tray_icon.show()
        self.tray_icon.showMessage('Misura Server', msg, msecs=level*50)
        self.updateStatusbar(msg)
        return True

    def focus_logging(self):
        self.logDock.show()

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
        if d:
            self.removeDockWidget(d)
            d.deleteLater()
        if not w:
            return
        w = getattr(self, w, False)
        if w:
            w.blockSignals(True)
            w.deleteLater()

    def set_addr(self, addr):
        entry = confdb.get_from_key('recent_server', addr)
        logging.debug('MainWindow.set_addr', addr, entry)
        user = entry[1]
        password = entry[2]
        mac = entry[3]
         
        self.login_window = connection.LoginWindow(
            addr, user=user, password=password, mac=mac, globalconn=False)
        self.login_window.login_failed.connect(
            self.retry_login, QtCore.Qt.QueuedConnection)
        self.login_window.login_succeeded.connect(
            self.succeed_login, QtCore.Qt.QueuedConnection)
        r = widgets.RunMethod(self.login_window.tryLogin, user, password, mac=mac)
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
        self.tasks_dock = QtGui.QDockWidget(self.centralWidget())
        self.tasks_dock.setWindowTitle("Pending Tasks")
        self.tasks_dock.setWidget(registry.taskswg)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.tasks_dock)

        registry.taskswg.show_signal.connect(self.pending_task_shown)
        registry.taskswg.hide_signal.connect(self.pending_task_hidden)
        self.connect(registry, QtCore.SIGNAL('logMessage(int, QString)'), self.notify)

    def pending_task_shown(self):
        self.tasks_dock.show()

    def pending_task_hidden(self):
        self.tasks_dock.hide()

    def closeEvent(self, ev):
        self.clean_interface()
        if not self.fixedDoc:
            registry.toggle_run(False)
            self.tasks.close()
        else:
            self.fixedDoc.proxy.close()
        ev.accept()
    

    _blockResetFileProxy = False    

    def setServer(self, server=False):
        self._blockResetFileProxy = True
        logging.debug('Setting server to', server)
        self.server = server
        if not server:
            network.manager.remote.connect()
            self.server = network.manager.remote
        if not self.fixedDoc:
            if not check_time_delta(self.server):
                return False
        registry.toggle_run(True)
        self.serverDock.hide()
        self.add_menubar()
        self.rem('logDock')
        self.logDock = QtGui.QDockWidget(self.centralWidget())
        self.logDock.setWindowTitle('Log Messages')
        if self.fixedDoc:
            self.logDock.setWidget(
                fileui.OfflineLog(self.fixedDoc.proxy, self.logDock))
        else:
            self.logDock.setWidget(LiveLog(self.logDock))
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.logDock)
        
        
        if not self.fixedDoc:
            self.rem('instrumentDock')
            self.instrumentDock = QtGui.QDockWidget(self.centralWidget())
            self.instrumentSelector = InstrumentSelector(self, self.setInstrument)
            self.instrumentDock.setWidget(self.instrumentSelector)
            self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.instrumentDock)
            registry.taskswg.sync.storage_sync.collect()
        else:
            self.instrumentDock = QtGui.QWidget()
        ri = self.server['runningInstrument']  # currently running
        # compatibility with old tests
        if ri in ['None', '']:
            ri = self.server['lastInstrument']  # configured, ready, finished

        if ri not in ['None', '']:
            remote = getattr(self.server, ri)
            self.updateInstrumentInterface_when_instrument_is_ready(remote)

        if self.fixedDoc:
            return True
        # Automatically pop-up delayed start dialog
        if self.server['delayStart']:
            self.delayed_start()
        return True

    def add_measure(self):
        self.rem('measureDock', 'measureTab')
        self.measureDock = QtGui.QDockWidget(self.centralWidget())
        self.measureDock.setWindowTitle(_('Test Configuration'))
        self.measureTab = MeasureInfo(
            self.remote, self.fixedDoc, parent=self.measureDock)
        self.measureDock.setWidget(self.measureTab)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.measureDock)

    def add_snapshots(self):
        self.rem('snapshotsDock', 'snapshotsStrip')
        self.snapshotsDock = QtGui.QDockWidget(self.centralWidget())
        self.snapshotsDock.setWindowTitle(_('Story Board'))
        self.imageSlider = fileui.ImageSlider()
        self.snapshotsDock.setWidget(self.imageSlider)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.snapshotsDock)
        if self.name not in ['hsm', 'post', 'drop']:
            self.snapshotsDock.hide()

    def add_sumtab(self):
        # SUMMARY TREE - In lateral measureTab
        self.measureTab.set_results(Results(self.measureTab, self.summaryPlot, self.server._readLevel))
        self.navigator = self.measureTab.results.navigator
        

    def add_graph(self):
        # PLOT window
        self.summaryPlot = graphics.Plot()
        self.graphWin = self.centralWidget().addSubWindow(
            self.summaryPlot, subWinFlags)
        self.graphWin.setWindowTitle(_('Data Plot'))
        self.graphWin.hide()

    def add_table(self):
        self.dataTable = fileui.SummaryView(parent=self)
        self.tableWin = self.centralWidget().addSubWindow(
            self.dataTable, subWinFlags)
        self.tableWin.hide()

    def _init_instrument(self, soft=False, name='default'):
        """Called in a different thread. Need to recreate connection."""
        r = self.remote.copy()
        r.connect()
        result = r.init_instrument(soft, name)


    def init_instrument(self, soft=False, name='default'):
        # TODO: this scheme could be automated via a decorator: @thread
        logging.debug('Calling init_instrument in QThreadPool')
        r = widgets.RunMethod(self._init_instrument, soft, name)
        r.pid = 'Instrument initialization '
        QtCore.QThreadPool.globalInstance().start(r)
        logging.debug('active threads:',
                      QtCore.QThreadPool.globalInstance().activeThreadCount(),
                      QtCore.QThreadPool.globalInstance().maxThreadCount())


    def updateInstrumentInterface(self, remote=False):
        name = remote['devpath']
        self.tasks.done('Waiting for server')

        if remote is False:
            remote = self.remote
        else:
            self.remote = remote

        self.clean_interface(remote)

        self.controls = Controls(self.remote, parent=self)
        logging.debug('Created controls')
        self.controls.stopped.connect(self.stopped)
        self.controls.started.connect(self.resetFileProxy)
        self.controls.mute = bool(self.fixedDoc)
        self.addToolBar(self.controls)
        self.toolbars.append(self.controls)
        logging.debug('Done controls')
        pid = self.instrument_pid()
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
        self.myMenuBar.setInstrument(remote, server=self.server)
        self.myMenuBar.show()

        # Populate Cameras
        self.tasks.job(-1, pid, 'Show cameras')
        paths = self.remote['devices']
        logging.debug('setInstrument PATHS:', paths)

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

        self.reset_instrument_timer.singleShot(
                500,
                lambda: windows.arrange(self.centralWidget(), self.name)
            )

        self.tasks.done(pid)
        return True

    def updateInstrumentInterface_when_instrument_is_ready(self, remote):
        if remote is False:
            remote = self.remote
        else:
            self.remote = remote

        self.clean_interface(remote)

        self.tasks.jobs(-1, 'Waiting for server')
        if self.remote['initInstrument'] != 0:
            self.reset_instrument_timer.singleShot(
                1000,
                lambda: self.updateInstrumentInterface_when_instrument_is_ready(
                    remote)
            )
            return False

        self.updateInstrumentInterface(remote)
        return True

    def clean_interface(self, remote=False):
        self._blockResetFileProxy = True
        self.instrumentDock.hide()
        self.remote = remote
        self.name = 'unknown'
        title = 'Misura Acquisition - Waiting'
        if self.remote:
            name = self.remote['devpath']
            self.name = name
            logging.debug('Setting remote ', remote, self.remote, name)
            title = _('Misura Acquisition: %s (%s)') %  (name, self.remote['comment'])
    
        self.setWindowTitle(title)
        self.tray_icon.setToolTip(title)
        pid = self.instrument_pid()
        self.tasks.jobs(11, pid)
        QtGui.qApp.processEvents()
        # Close cameras
        for p, (pic, win) in self.cameras.iteritems():
            logging.debug('deleting cameras', p, pic, win)
            pic.close()
            win.hide()
            win.close()
            win.deleteLater()
        self.cameras = {}
        QtGui.qApp.processEvents()

        self.tasks.job(1, pid, 'Preparing menus')
        self.add_menubar(setInstrument=False)
        #self.myMenuBar.close()
        #self.myMenuBar = MenuBar(server=self.server, parent=self)
        #self.setMenuWidget(self.myMenuBar)
        logging.debug('Done menubar')

        # Remove any remaining subwindow
        self.centralWidget().closeAllSubWindows()

        self.tasks.job(1, pid, 'Controls')
        for tb in self.toolbars:
            self.removeToolBar(tb)
            tb.close()
            del tb
        self.toolbars = []
        logging.debug('Cleaned toolbars')

    def setInstrument(self, remote=False, server=False, preset='default'):
        if self.fixedDoc:
            return False

        if server is not False:
            self.setServer(server)
        if remote is False:
            remote = self.remote
        else:
            self.remote = remote

        if self.server['isRunning']:
            return False

        self.clean_interface(remote)

        self.init_instrument(soft=True, name=preset)
        sleep(0.5)
        self.updateInstrumentInterface_when_instrument_is_ready(remote)



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

        logging.debug('imageSlider')
        self.tasks.job(-1, pid, 'Sync snapshots with document')
        self.imageSlider.set_doc(doc)

        logging.debug('summaryPlot')
        self.tasks.job(-1, pid, 'Sync graph with document')
        self.summaryPlot.set_doc(doc)
        self.connect_statusbar()

        logging.debug('navigator')
        self.tasks.job(-1, pid, 'Sync document tree')
        self.navigator.set_doc(doc)
        self.server._navigator = self.navigator

        self.measureTab.set_doc(doc)

        logging.debug('dataTable')
        self.tasks.job(-1, pid, 'Sync data table')
        self.dataTable.set_doc(doc)
        logging.debug('connect')
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

    @csutil.unlockme
    def _resetFileProxy(self, retry=0, recursion=0):
        """Resets acquired data widgets"""
        if self._blockResetFileProxy:
            return False

        if self.doc:
            self.doc.close()
            self.doc = False

        doc = False
        fid = False

        live_file = self.get_live_file_or_retry_later(retry, recursion)

        if live_file:
            try:
                fp = RemoteFileProxy(live_file, conf=self.server, live=True)
                self.refresh_header()
                doc = filedata.MisuraDocument(proxy=fp)
                # Remember as the current uid
                self.uid = fid
            except:
                logging.debug('RESETFILEPROXY error')
                logging.debug(format_exc())
                doc = False
                self.resetFileProxyLater(retry + 1, recursion + 1)
                return

            self._finishFileProxy(doc)

    def refresh_header(self):
        self.server.storage.test.live.header(['Array', 'FixedTimeArray'], False, True)


    def get_live_file_or_retry_later(self, retry, recursion):
        live_uid = self.get_live_uid_or_retry_later(retry, recursion)

        if live_uid:
            live_file = getattr(self.server.storage.test, live_uid)

            if not live_file.has_node('/conf'):
                live_file.load_conf()

                if not live_file.has_node('/conf'):
                    logging.debug('Conf node not found: acquisition has not been initialized.')
                    self.tasks.job(0, 'Waiting for data',
                                   'Conf node not found: acquisition has not been initialized.')
                    self.tasks.done('Waiting for data')
                    return False
            return live_file

        return False

    def get_live_uid_or_retry_later(self, retry, recursion):
        if self.server['initTest'] or self.server['closingTest']:
            self.tasks.jobs(0, 'Test initialization')
            if recursion == 0:
                self.tasks.setFocus()
            logging.debug('Waiting for initialization to complete...')
            self.resetFileProxyLater(0, recursion + 1)
            return False
        else:
            if not self.server['isRunning']:
                retry = self.max_retry
            self.tasks.jobs(self.max_retry, 'Waiting for data')
            self.tasks.done('Test initialization')
            self.tasks.job(retry, 'Waiting for data')
            if retry < self.max_retry and self.remote.measure['elapsed'] < 10:
                self.resetFileProxyLater(retry + 1, recursion + 1)
                return False
            if retry > self.max_retry:
                self.tasks.done('Waiting for data')
                QtGui.QMessageBox.critical(self, _('Impossible to retrieve the ongoing test data'),
                                           _("""A communication error with the instrument does not allow to retrieve the ongoing test data.
                        Please restart the client and/or stop the test."""))
                return False
            fid = self.remote.measure['uid']
            if fid == '':
                logging.debug('no active test', fid)
                self.tasks.done('Waiting for data')
                return False
            logging.debug('resetFileProxy to live ', fid)
            self.server.connect()

            live_uid = self.server.storage.test.live.get_uid()

            if not live_uid:
                logging.debug('No live_uid returned')
                return False

            if fid == self.uid:
                logging.debug(
                    'Measure id is still the same. Aborting resetFileProxy.')
                self.tasks.job(0, 'Waiting for data',
                               'Measure id is still the same. Aborting resetFileProxy.')
                self.tasks.done('Waiting for data')
                return False

        return live_uid

    def resetFileProxy(self, *a, **k):
        """Locked version of resetFileProxy"""
        if not self._lock.acquire(False):
            logging.debug('ANOTHER RESETFILEPROXY IS RUNNING!')
            return False

        if self.fixedDoc is not False:
            fid = 'fixedDoc'
            doc = self.fixedDoc
            self._finishFileProxy(doc)
            doc.reloadData()
            self._lock.release()
            return False

        self._blockResetFileProxy = False
        logging.debug('MainWindow.resetFileProxy: Stopping registry')

        registry.stop_updating_doc()

        self._resetFileProxy(*a, **k)

    def _finishFileProxy(self, doc):
        self.tasks.done('Waiting for data')
        logging.debug('RESETFILEPROXY', doc.proxy_filename, doc.data.keys(), doc.up)
        self.set_doc(doc)
        logging.debug('MainWindow.resetFileProxy: Restarting registry')

        registry.restart_updating_doc()
        registry.toggle_run(True)
        doc.up = True

        self.tasks.done('Waiting for data')
        if not self.fixedDoc:
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

    def stopped(self):
        """Offer option to download the remote file"""
        registry.toggle_run(False)

        uid = self.remote.measure['uid']
        logging.debug('acquisition.MainWindow.stopped', uid)
        if uid in self.saved_set:
            logging.debug('UID already saved!', uid)
            return False
        self.saved_set.add(uid)

        if self.doc:
            self.doc.close()
        self.set_doc(False)

        dbpath = confdb['database']
        if not os.path.exists(dbpath):
            logging.debug('A non-existent db path was specified', dbpath)
            return False

        # Start download thread
        self.server.storage.refresh()
        sy = TransferThread(outfile=False, uid=uid, server=self.server, dbpath=dbpath)
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
        self.db3Dia = misura3.TestDialog(self)
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
        f = tables.open_file(filename, 'r')
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
        logging.debug('SEARCH UID', r)
        if not r:
            return False
        self.remote.init_uid(uid)
        # Attiva lo streaming se è spento
        for cam, win in self.cameras.itervalues():
            cam.toggle(1)
        return True
