
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
        urls = drop_event.mimeData().urls()
        logging.debug('dropEvent', urls)
        for url in urls:
            url = url.toString().replace('file://', '')
            # on windows, remove also the first "/"
            if os.name.lower() == 'nt':
                url = url[1:]
            self.convert.emit(url)


class MainWindow(QtGui.QMainWindow):

    """Open single files, local databases, remote databases."""

    def __init__(self, parent=None):
        super(QtGui.QMainWindow, self).__init__(parent)
        configure_logger('browser.log')
        self.tab = QtGui.QTabWidget()
        self.setAcceptDrops(True)
        self.area = DatabasesArea(self)
        self.tab.addTab(self.area, _('Databases'))
        self.tab.setTabsClosable(True)
        self.tab.setDocumentMode(True)
        database_tab_index = 0
        self.remove_close_button_from_tab(database_tab_index)
        self.setCentralWidget(self.tab)
        self.setMinimumSize(800, 600)
        self.setWindowTitle(_('Misura Browser'))
        self.myMenuBar = menubar.BrowserMenuBar(parent=self)
        self.setMenuWidget(self.myMenuBar)

        self.connect(
            self.tab, QtCore.SIGNAL('tabCloseRequested(int)'), self.close_tab)

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

    def closeEvent(self, event):
        iutils.app.quit()
        
    def convert_file(self, path):
        filedata.convert_file(self,path)
        
    def _open_converted(self):
        test_window = self.open_file(self.converter.outpath)
        self.converter.post_open_file(test_window.navigator)

    def _failed_conversion(self, error):
        QtGui.QMessageBox.warning(self, _("Failed conversion"), error)

    def open_file(self, path, tab_index=-1, **kw):
        path = unicode(path)
        logging.debug('Browser MainWindow.open_file', path, tab_index)
        if tab_index>0:
            tab = self.tab.widget(tab_index)
            tab.measureTab.results.navigator.open_file(path)
            return
        
        try:
            doc = filedata.MisuraDocument(path)
        except Exception as error:
            logging.error(format_exc())
            self.myMenuBar.recentFile.conf.rem_file(path)
            QtGui.QMessageBox.warning(self, 'Error', str(error))
            return False

        tw = testwindow.TestWindow(doc)
        instrument = doc.proxy.conf['runningInstrument']
        cw = self.centralWidget()
        icon = QtGui.QIcon(os.path.join(parameters.pathArt, 'small_' + instrument + '.svg'))
        win = cw.addTab(tw, icon, tw.title)
        confdb.mem_file(path, tw.remote.measure['name'])
        cw.setCurrentIndex(cw.count() - 1)
        return tw

    def open_database(self, path, new=False):
        idb = getDatabaseWidget(path, new=new, browser=self)
        win = self.area.addSubWindow(idb)
        win.show()
        confdb.mem_database(path)
        self.connect(
            idb, QtCore.SIGNAL('selectedFile(QString)'), self.open_file)
        self.connect(
            idb, QtCore.SIGNAL('selectedFile(QString,int)'), self.open_file)

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
            return
        w = self.tab.widget(idx)
        if w.check_save():
            self.tab.removeTab(idx)
            w.close()
            # explicitly destroy the widget
            del w

    def remove_close_button_from_tab(self, tab_index):
        self.tab.tabBar().tabButton(
            tab_index, QtGui.QTabBar.RightSide).resize(0, 0)
