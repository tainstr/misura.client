
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore
import os

from misura.client import configure_logger


from .. import _
from .. import confwidget
from .. import filedata

from ..clientconf import confdb
from .. import iutils

from ..database import getDatabaseWidget, getRemoteDatabaseWidget
from .. import parameters

from . import menubar
from . import testwindow

from traceback import print_exc, format_exc

try:
    from .. import misura3
except:
    print_exc()
    misura3 = False




def decode_drop_event(drop_event):
    urls = drop_event.mimeData().urls()
    logging.debug('dropEvent', urls)
    for url in urls:
        # on windows, remove also the first "/"
        if os.name.lower() == 'nt':
            url = url.toString()
            if url.startswith('file:///'):
                url = url[8:]
            elif url.startswith('file:'):
                url = url[5:]
        else:
            url = url.toString().replace('file://', '')
        return url
    return False

class DatabasesArea(QtGui.QMdiArea):
    convert = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(DatabasesArea, self).__init__(parent)
        self.setAcceptDrops(True)
        self.pix_size = QtCore.QSize(500, 100)
        self.pix = iutils.theme_icon("browser_drag_drop").pixmap(self.pix_size)
        self.gray = self.background()
        
    def resizeEvent(self, event):
        """Add the drag-n-drop artwork"""
        size = event.size()
        new_back = QtGui.QImage(size, QtGui.QImage.Format_ARGB32_Premultiplied)
        paint = QtGui.QPainter(new_back)
        paint.fillRect(0, 0, size.width(), size.height(), self.gray)
        paint.drawPixmap(size.width()-self.pix_size.width(), 
                         size.height()-self.pix_size.height(), 
                         self.pix, 0, 0, 0 , 0)
        paint.end()
        self.setBackground(QtGui.QBrush(new_back))
        return QtGui.QMdiArea.resizeEvent(self, event)

    def dragEnterEvent(self, event):
        logging.debug('dragEnterEvent', event.mimeData())
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, drop_event):
        url = decode_drop_event(drop_event)
        if url:
            self.convert.emit(url)

class TestsTabBar(QtGui.QTabBar):
    dropped = QtCore.pyqtSignal(str)
    
    def __init__(self, *a, **k):
        super(TestsTabBar, self).__init__(*a, **k)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        logging.debug('TestsTabBar.dragEnterEvent', event.mimeData())
        if event.mimeData().hasUrls():
            event.acceptProposedAction()    
    
    def dropEvent(self, drop_event):
        url = decode_drop_event(drop_event)
        if url:
            self.dropped.emit(url)        

class MainWindow(QtGui.QMainWindow):

    """Open single files, local databases, remote databases."""

    def __init__(self, parent=None):
        super(QtGui.QMainWindow, self).__init__(parent)
        self.opened_windows = []
        self.tab = QtGui.QTabWidget()
        self.tab_bar = TestsTabBar()
        self.tab_bar.dropped.connect(self.convert_file)
        self.tab.setTabBar(self.tab_bar)
        self.setAcceptDrops(True)
        self.area = DatabasesArea(self)
        self.tab.addTab(self.area, _('Databases'))
        self.tab.setTabsClosable(True)
        self.tab.setDocumentMode(True)
        self.memory_timer = QtCore.QTimer()
        self.memory_timer.timeout.connect(iutils.memory_check)
        self.memory_timer.start(2000)

        
        database_tab_index = 0
        self.remove_close_button_from_tab(database_tab_index)
        self.setCentralWidget(self.tab)
        self.setMinimumSize(800, 600)
        self.setWindowTitle(_('Misura Browser'))
        self.myMenuBar = menubar.BrowserMenuBar(parent=self)
        self.setMenuWidget(self.myMenuBar)
        
        self.tab.tabCloseRequested.connect(self.close_tab)
        self.tab.currentChanged.connect(self.current_tab_changed)

        self.connect(self, QtCore.SIGNAL(
            'do_open(QString)'), self.open_file)

        self.connect(self.myMenuBar.recentFile, QtCore.SIGNAL(
            'select(QString)'), self.open_file)

        self.connect(self.myMenuBar.recentFile, QtCore.SIGNAL(
            'convert(QString)'), self.convert_file)

        self.area.convert.connect(self.convert_file)

        self.connect(self.myMenuBar.recentDatabase, QtCore.SIGNAL(
            'select(QString)'), self.open_database)
        self.connect(self.myMenuBar, QtCore.SIGNAL(
            'new_database(QString)'), self.new_database)

        # Recent objects greeter window:
        greeter = confwidget.Greeter(parent=self)
        greeter.file.select.connect(self.open_file)
        greeter.file.add_to.connect(self.open_file)
        greeter.file.convert.connect(self.convert_file)
        greeter.database.select.connect(self.open_database)

        if confdb['m3_enable'] and misura3:
            
            greeter.m3database.select.connect(self.open_m3db)
            self.myMenuBar.recentM3db.select.connect(self.open_m3db)

        win = self.area.addSubWindow(greeter,
                                     QtCore.Qt.CustomizeWindowHint |
                                     QtCore.Qt.WindowTitleHint |
                                     QtCore.Qt.WindowMinMaxButtonsHint)

        self.setWindowIcon(
            QtGui.QIcon(os.path.join(parameters.pathArt, 'browser.svg')))
        
        self.open_database(confdb['database'])
        

    def closeEvent(self, event):
        logging.debug('closeEvent')
        i = 0
        while self.tab.count()>1:
            logging.debug('Closing tab:', i)
            if not self.close_tab(1):
                event.ignore()
                return True
            i += 1
            
        try:
            confdb._lock.acquire(block=True, timeout=5)
            confdb._lock.release()
        except:
            logging.debug(format_exc())
        ret = QtGui.QMainWindow.closeEvent(self, event)
        iutils.app.quit()
        return ret
        
    def convert_file(self, path):
        filedata.convert_file(self,path)
        
    def _open_converted(self):
        test_window = self.open_file(self.converter.outpath)
        self.converter.post_open_file(test_window.navigator)

    def _failed_conversion(self, error):
        QtGui.QMessageBox.warning(self, _("Failed conversion"), error)

    def open_file(self, path, tab_index=-1, **kw):
        path = os.path.abspath(unicode(path))
        logging.debug('Browser MainWindow.open_file', path, tab_index)
        for i in xrange(1,self.tab.count()):
            if tab_index>0:
                break
            tab_path = os.path.abspath(self.tab.widget(i).fixedDoc.proxy.get_path())
            if path == tab_path:
                logging.debug('File is already opened: switching to tab', i)
                self.tab.setCurrentIndex(i)
                return False
            
        if tab_index>0:
            tab = self.tab.widget(tab_index)
            tab.measureTab.results.navigator.open_file(path)
            return False
        
        try:
            doc = filedata.MisuraDocument(path)
        except Exception as error:
            logging.error(format_exc())
            self.myMenuBar.recentFile.conf.rem_file(path)
            QtGui.QMessageBox.warning(self, 'Error', str(error))
            return False
        tw = testwindow.TestWindow(doc)
        tw.fixedDoc.model.sigPageChanged.connect(self.manage_caches)
        instrument = doc.proxy.conf['runningInstrument']
        cw = self.centralWidget()
        icon = QtGui.QIcon(os.path.join(parameters.pathArt, 'small_' + instrument + '.svg'))
        idx = cw.addTab(tw, icon, tw.title)
        self.tab_bar.setTabToolTip(idx, tw.toolTip())
        tw.loaded_version.connect(self.update_tooltip)
        confdb.mem_file(path, tw.remote.measure['name'])
        self.opened_windows.append(tw)
        cw.setCurrentIndex(idx)
        self.update_tooltip(tw)
        return tw
    
    def current_tab_changed(self, idx):
        """Refresh accessed tests queue"""
        if idx==0:
            return
        w = self.tab.widget(idx)
        if w in self.opened_windows:
            self.opened_windows.remove(w)
        self.opened_windows.append(w)
    
    def manage_caches(self, *a):
        logging.debug('manage_caches', self.opened_windows)
        for w in self.opened_windows:
            logging.debug('manage_caches for window:', w.windowTitle())
            w.slot_manage_cache()
    
    def update_tooltip(self, test_window):
        idx = self.tab.indexOf(test_window)
        self.tab_bar.setTabToolTip(idx, test_window.get_tooltip())

    def open_database(self, path, new=False):
        idb = getDatabaseWidget(path, new=new, browser=self)
        if not idb:
            logging.error('Failed opening database widget at', path)
            return False
        win = self.area.addSubWindow(idb)
        win.show()
        confdb.mem_database(path)
        self.connect(
            idb, QtCore.SIGNAL('selectedFile(QString)'), self.open_file)
        self.connect(
            idb, QtCore.SIGNAL('selectedFile(QString,int)'), self.open_file)
        return idb

    def new_database(self, path):
        self.open_database(path, new=True)

    def open_server(self, addr):
        idb = getRemoteDatabaseWidget(addr)
        if not idb:
            return False
        win = self.area.addSubWindow(idb)
        win.show()
        self.connect(
            idb, QtCore.SIGNAL('selectedRemoteUid(QString,QString)'), self.open_remote_uid)
        return True

    def open_remote_uid(self, addr, uid):
        addr = str(addr)
        uid = str(uid)
        path = addr + '|' + uid
        self.open_file(path)

    def open_m3db(self, path):
        m3db = misura3.TestDialog(path=path)
        m3db.img = True
        m3db.keep_img = True
        m3db.force = False
        self.connect(
            m3db, QtCore.SIGNAL('select(QString)'), self.open_file)
        confdb.mem_m3database(path)
        win = self.area.addSubWindow(m3db)
        win.show()
        
    def list_tabs(self):
        return [self.tab.widget(i) for i in range(self.tab.count())]
            

    def close_tab(self, idx):
        logging.debug('Tab close requested', idx)
        if idx == 0:
            return False
        w = self.tab.widget(idx)
        if w and w.check_save(nosync=False):
            if w in self.opened_windows:
                self.opened_windows.remove(w)
            self.tab.removeTab(idx)
            w.close()
            return True
        # Failed to close the tab
        return False

    def remove_close_button_from_tab(self, tab_index):
        self.tab.tabBar().tabButton(
            tab_index, QtGui.QTabBar.RightSide).resize(0, 0)
