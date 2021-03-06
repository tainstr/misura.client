#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools

from PyQt4 import QtGui, QtCore

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.plugin import dataimport

from . import _
from . import iutils
from .clientconf import confdb, settings, default_misuradb_path




class Path(QtGui.QWidget):

    def __init__(self, path, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.lay = QtGui.QHBoxLayout()
        self.setLayout(self.lay)
        self.lay.addWidget(QtGui.QLabel(_('Configuration File:')))
        self.line = QtGui.QLineEdit(self)
        self.line.setText(path)
        self.lay.addWidget(self.line)
        self.button = QtGui.QPushButton(self)
        self.button.setText(_('Open'))
        self.lay.addWidget(self.button)
        self.connect(self.button, QtCore.SIGNAL('clicked()'), self.change)

        self.btn_reload = QtGui.QPushButton(self)
        self.btn_reload.setText(_('Reload'))
        self.lay.addWidget(self.btn_reload)
        self.connect(self.btn_reload, QtCore.SIGNAL('clicked()'), self.reload)

        self.btn_save = QtGui.QPushButton(self)
        self.btn_save.setText(_('Save'))
        self.lay.addWidget(self.btn_save)
        self.connect(self.btn_save, QtCore.SIGNAL('clicked()'), self.save)

    def reload(self):
        self.emit(QtCore.SIGNAL('newDb()'))

    def save(self):
        check_default_database()
        confdb.save()

    def change(self):
        path = QtGui.QFileDialog.getOpenFileName(
            parent=self, caption=_("Client configuration path"))
        if not path:
            return
        self.line.setText(path)
        self.reload()


class ClientConf(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.path = Path(confdb.path, self)
        self.lay.addWidget(self.path)
        from misura.client import conf
        self.conf = conf.Interface(confdb, confdb, confdb.describe())
        self.lay.addWidget(self.conf)
        self.connect(self.path, QtCore.SIGNAL('newDb()'), self.change)
        self.connect(self.path, QtCore.SIGNAL('save()'), confdb.save)

    def change(self):
        path = str(self.path.line.text())
        r = confdb.load(path)
        self.conf.close()
        del self.conf
        from misura.client import conf
        self.conf = conf.Interface(confdb, confdb, confdb.describe())
        self.lay.addWidget(self.conf)
        settings.setValue('/Configuration', path)


class RecentInterface(object):
    """Common functions for recent elements management"""
    open_new = QtCore.pyqtSignal(str)
    select = QtCore.pyqtSignal(str)
    convert = QtCore.pyqtSignal(str)
    

    def __init__(self, conf, category):
        super(RecentInterface, self).__init__()
        self.category = category
        self.conf = conf
        self.name = category
        if self.name == 'm3database':
            self.name = 'Misura3 database'
            self.label = self.name
        else:
            self.label = 'Recent {}'.format(self.name.capitalize())
            

    def getNameSigList(self):
        tab = self.conf['recent_' + self.category]
        logging.debug('getNameSigList', self.category, tab)
        nsl = []
        for i, row in enumerate(reversed(tab[1:])):
            sig = row[0]
            name = row[0]
            if self.category == 'file':
                if row[1] != '':
                    name = row[1] + ' (' + iutils.shorten(row[0]) + ')'
            if self.category == 'server':
                name0 = row[0].replace('//', '/').split('/')[1]
                name = row[1] + '@' + name
#               sig='https://%s:%s@%s/RPC' % (row[1],row[2],name0)
            nsl.append([name, sig, row])
        return nsl

    def clear_recent(self):
        logging.debug('ConfWidget: Clearing recent entries')
        tname = 'recent_' + self.category
        self.conf[tname] = self.conf[tname][0] 
        self.conf.save()
        self.conf.emit(QtCore.SIGNAL('rem()'))

    def new(self, *a):
        if self.category in ['server']:
            path = QtGui.QInputDialog.getText(self, _('Specify a new server address'), _(
                'Address'), text='https://IP:3880/RPC')[0]
        else:
            d= self.conf.last_directory(self.category)
            path = QtGui.QFileDialog.getOpenFileName(
                self.parent(), _("Open a new ") + self.category, d)
        if not path:
            return
        self.open_new.emit(path)
        self.select.emit(path)

    def data_import(self, *a):
        d= self.conf.last_directory(self.category)
        file_filter = ''
        for converter in dataimport.data_importers:
            file_filter += '{} ({});;'.format(_(converter.name), converter.file_pattern.replace(';', ' '))
            print('adding filter', file_filter)
        path = QtGui.QFileDialog.getOpenFileName(
            self.parent(), _("Data import"),
            d,
            file_filter)
        self.convert.emit(path)


def addNameSigList_to_menu(menu, nsl, emitter=False):
    r = []
    emitter = emitter or menu
    for name, sig, row in nsl:
        p = functools.partial(
            emitter.emit, QtCore.SIGNAL('select(QString)'), sig)
        a = menu.addAction(name, p)
        a.setToolTip('\n'.join(row))
        r.append(a)
    return r
    

class RecentMenu(RecentInterface, QtGui.QMenu):
    """Recent objects menu"""
    open_new = QtCore.pyqtSignal(str)
    select = QtCore.pyqtSignal(str)
    convert = QtCore.pyqtSignal(str)
    server_disconnect = QtCore.pyqtSignal()
    server_shutdown = QtCore.pyqtSignal()
    server_restart = QtCore.pyqtSignal()

    _detached = False
    
    def __init__(self, conf, category, parent=None):
        QtGui.QMenu.__init__(self, parent=parent)
        RecentInterface.__init__(self, conf, category)
        tit = _('Recent {}s'.format(self.name))
        self.setTitle(tit)
        self.setWindowTitle(tit)
        self.setTearOffEnabled(True)
        self.redraw()
        self.connect(self.conf, QtCore.SIGNAL('mem()'), self.redraw)
        self.connect(self.conf, QtCore.SIGNAL('rem()'), self.redraw)
        self.connect(self, QtCore.SIGNAL('aboutToShow()'), self.redraw)

    def redraw(self):
        self.clear()
        self.setTearOffEnabled(True)
        nsl = self.getNameSigList()
        addNameSigList_to_menu(self, nsl)
        self.addSeparator()
        self.addAction(_("Clear list"), self.clear_recent)
        self.addAction(_("Open") + '...', self.new)
        if self.name == 'file' and len(dataimport.data_importers) > 0:
            self.addAction(_("Import") + '...', self.data_import)
        if self.category == 'server':
            
            self.addAction(_('Disconnect'), self.server_disconnect.emit)
            self.addAction(_('Restart'), self.server_restart.emit)
            self.addAction(_('Shutdown'), self.server_shutdown.emit)
        self.addSeparator()
        self.addAction(_('Detach'), self.detach)
        
    def detach(self):
        if self._detached:
            self._detached.hide()
            self._detached.close()
        wg = RecentWidget(self.conf, self.category)
        wg.route_select = lambda *a: self.select.emit(*a)
        wg.route_convert = lambda *a: self.convert.emit(*a)
        #wg.connect(wg, QtCore.SIGNAL('select(QString)'),wg.route_select)
        wg.select.connect(self.select.emit)
        wg.convert.connect(self.convert.emit)
        wg.open_new.connect(self.open_new.emit)
        wg.setWindowTitle(self.windowTitle())
        wg.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        wg.show()
        self._detached = wg
        


class RecentWidget(RecentInterface, QtGui.QWidget):

    """Recent objects list widget"""
    open_new = QtCore.pyqtSignal(str)
    select = QtCore.pyqtSignal(str)
    add_to = QtCore.pyqtSignal(str, int)
    convert = QtCore.pyqtSignal(str)
    
    def __init__(self, conf, category, parent=None):
        QtGui.QWidget.__init__(self, parent)
        RecentInterface.__init__(self, conf, category)
        self.setWindowTitle(_('Recent ' + self.name + 's:'))
        self.lay = QtGui.QVBoxLayout()
        self.menu = QtGui.QMenu()
        self.lay.addWidget(QtGui.QLabel('Recent ' + self.name + 's:'))

        self.list = QtGui.QListWidget(self)
        self.list.itemDoubleClicked.connect(self.select_item)
        self.list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.show_context_menu)
        self.list.itemSelectionChanged.connect(self.pre_select_item)
        self.connect(self.conf, QtCore.SIGNAL('mem()'), self.redraw)
        self.connect(self.conf, QtCore.SIGNAL('rem()'), self.redraw)
        self.lay.addWidget(self.list)

        self.open_button = QtGui.QPushButton(_('Open Selected'), parent=self)
        self.open_button.setIcon(iutils.theme_icon('document-new'))
        self.open_button.setEnabled(False)
        self.connect(
            self.open_button, QtCore.SIGNAL('clicked()'), self.select_item)
        self.lay.addWidget(self.open_button)
        
        lbl = {'file': ' Misura file'}.get(category, '')
        self.add_button = QtGui.QPushButton(_('Open another') +lbl + ' ...', parent=self)
        if self.name == 'server':
            icon = iutils.theme_icon('connect')
        else:
            icon = iutils.theme_icon('system-file-manager')
        self.add_button.setIcon(icon)
        
        self.connect(self.add_button, QtCore.SIGNAL('clicked()'), self.new)
        self.lay.addWidget(self.add_button)
        
        if category == 'file' and len(dataimport.data_importers) > 0:
            self.import_button = QtGui.QPushButton(
                _('Import from') + '...', parent=self)
            self.connect(
                self.import_button, QtCore.SIGNAL('clicked()'), self.data_import)
            self.lay.addWidget(self.import_button)

        self.redraw()
        self.setLayout(self.lay)

    def redraw(self):
        """Updates the list"""
        self.list.clear()
        nsl = self.getNameSigList()
        for name, sig, row in nsl:
            item = QtGui.QListWidgetItem(name)
            # Assign to the item userdata the path of the object, which will be
            # emitted in select_item
            item.setData(QtCore.Qt.UserRole, sig)
            item.setToolTip('\n'.join(row))
            self.list.addItem(item)
            
    def pre_select_item(self, item=False):
        print('Preselect', item)
        if not item:
            item = self.list.currentItem()
            self.open_button.setEnabled(True)
        if not item:
            self.open_button.setEnabled(False)
            return False
        return item   
        
    
    def show_context_menu(self, pt):
        item = self.pre_select_item()
        if not item:
            logging.debug('No item selected: cannot show context menu')
        self.menu.clear()
        self.menu.addAction(_('Open'), self.select_item)
        self.menu.addAction(_('Remove recent'), self.remove_recent)
        if self.category=='file':
            self.add_to_browser_windows(item)
        
        self.menu.exec_(self.list.mapToGlobal(pt))
        
    def add_to_browser_windows(self, item):
        browser = self.parent().parent().parent().parent().parent().parent().parent()
        self.menu.addSeparator()
        for i,tab in enumerate(browser.list_tabs()[1:]):
            open_function = functools.partial(self.add_to.emit,
                                              item.data(QtCore.Qt.UserRole),
                                              i+1)
            self.menu.addAction(tab.title, open_function)
            
        
        
    def remove_recent(self, item=False):
        item = self.pre_select_item(item)
        sig = item.data(QtCore.Qt.UserRole)
        logging.debug('Removing recent:', item.text(), sig)
        self.conf.rem(self.category, sig)
           

    def select_item(self, item=False):
        """Emit the 'select(QString)' signal with the path of the object"""
        item = self.pre_select_item(item)
        if item:
            self.select.emit(
                      item.data(QtCore.Qt.UserRole))
            
        

class Greeter(QtGui.QWidget):

    """Group of recent object widgets, for file, database and server items."""

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.lay = QtGui.QHBoxLayout()
        self.setWindowTitle('Recent data sources')

        self.file = RecentWidget(confdb, 'file', self)
        self.lay.addWidget(self.file)
        self.database = RecentWidget(confdb, 'database', self)
        self.lay.addWidget(self.database)
        if confdb['m3_enable']:
            self.m3database = RecentWidget(confdb, 'm3database', self)
            self.lay.addWidget(self.m3database)
        # self.server = RecentWidget(confdb, 'server', self)
#        self.lay.addWidget(self.server)

        self.setLayout(self.lay)
        
import os

empty_db_msg = _("""The default database was not configured.
Completed tests cannot be downloaded anywhere.
Please select now a new or existing database file (Ok), 
or Cancel to accept the default path:\n""") + default_misuradb_path
missing_db_msg = _("""The default database was not found in the configured path:\
{}
Please be sure any external/network drive is connected.
Please select now a new or existing database file (Ok), 
or (Cancel) to accept the default path:\n""") + default_misuradb_path
invalid_db_msg = _('The Misura database cannot reside within the installation folder:\
\n\n{}\n\t resides in: \n{}\n\n\
Please choose another file path, otherwise the database will be wiped every time Misura is updated.')

def check_default_database():
    from . import parameters as params
    db = confdb['database']
    if db.startswith(params.pathClient):
        QtGui.QMessageBox.critical(None, _('Invalid database path'), 
                                   invalid_db_msg.format(db, 
                                                        params.pathClient))
        db = ''   
    if not os.path.exists(db):
        if not db:
            r = QtGui.QMessageBox.warning(None, _('No default database was configured'), empty_db_msg,
                                          QtGui.QMessageBox.Cancel|QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        else:
            r = QtGui.QMessageBox.warning(None, _('Default database was not found'), missing_db_msg.format(db),
                                          QtGui.QMessageBox.Cancel|QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        
        if r==QtGui.QMessageBox.Cancel:
            confdb['database'] = default_misuradb_path
        else:
            fname = QtGui.QFileDialog.getSaveFileName(
                None, 'Choose the default database path', 
                default_misuradb_path, 
                "SQLite (*.sqlite);;Misuradb (misuradb)",
                options = QtGui.QFileDialog.DontConfirmOverwrite)
            if fname.startswith(params.pathClient):
                QtGui.QMessageBox.critical(None, _('Invalid database path'), 
                                           invalid_db_msg.format(fname, 
                                                                 params.pathClient))
                # Reconfigure
                return check_default_database()
            if fname:
                confdb['database'] = fname
            else:
                confdb['database'] = default_misuradb_path
        
        confdb.save()
    return True
