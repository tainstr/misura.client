#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Database synchronization service and widget"""
import os

from traceback import format_exc

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from .. import _
from ..clientconf import confdb
from misura.canon import indexer
from ..network import TransferThread, remote_dbdir
from .sync_table_model import SyncTableModel
from .. import database

from PyQt4 import QtCore, QtGui

record_length = len(indexer.indexer.testColumn)


class StorageSync(object):

    """Storage synchronization utilities"""
    chunk = 25
    """Max UID collect request"""
    server = False
    serial = False
    start = 0
    tot = 0

    def __init__(self, transfer=False):
        self.transfer = transfer
        """Object implementing a download_url(url,outfile) method"""

    def set_server(self, server):
        """Sets remote server towards which to run the synchronization service"""
        self.server = server
        self.remote_dbdir = remote_dbdir(server)
        """Remote db directory"""
        self.serial = self.server['eq_sn']
        """Server serial number"""
        self.tot = self.server.storage.get_len()
        if self.tot is None:
            self.tot = 0
        self.start = self.tot - self.chunk
        if self.start < 0:
            self.start = 0
        return True

    def set_dbpath(self, dbpath):
        """Set the local database path for storage synchronization"""
        if not dbpath:
            dbpath = confdb['database']
        self.dbpath = dbpath
        if not os.path.exists(self.dbpath):
            logging.debug('Database path does not exist!', self.dbpath)
            return False
        self.maindb = indexer.Indexer(self.dbpath)
        self.db = indexer.Indexer(self.dbpath + '.sync')
        return True

    def prepare(self, dbpath=False, server=False):
        """Open database and prepare operations"""
        if not self.set_dbpath(dbpath):
            return False
        if server:
            self.set_server(server)
        return True

    def has_uid(self, uid, tname):
        """Check if `uid` is in table `tname`"""
        r = self.db.execute_fetchall(
            "SELECT 1 from {} where uid='{}'".format(tname, unicode(uid)))
        return len(r)

    def rem_uid(self, uid, tname):
        """Remove `uid` from table `tname`"""
        self.db.execute("DELETE from {} where uid='{}'".format(tname, uid))
        logging.debug('removed uid', tname, uid)

    def add_record(self, record, tname):
        """Adds `record` list to table `tname`"""
        v = ('?,' * len(record))[:-1]
        self.db.execute("INSERT INTO {} VALUES ({})".format(tname, v), record)
        logging.debug('added record', tname, record)

    def download_record(self, record):
        uid = record[2]
        if self.has_uid(uid, 'sync_approve'):
            self.rem_uid(uid, 'sync_approve')

        if self.has_uid(uid, 'sync_exclude'):
            logging.debug('Record was excluded. Enabling.', record)
            self.rem_uid(uid, 'sync_exclude')

        if self.has_uid(uid, 'sync_error'):
            logging.debug('Retrying: ', record)
            self.rem_uid(uid, 'sync_error')

        if len(record) > record_length:
            record = record[:record_length]

        uid = record[indexer.indexer.col_uid]
        self.transfer.dbpath = self.dbpath
        self.transfer.uid = uid
        self.transfer.server = self.server
        self.transfer.start()

        return True

    def exclude_record(self, record):
        """Exclude `record` for download."""
        # Check if previously approved (remove!) or already excluded (exit)
        uid = record[2]
        if self.has_uid(uid, 'sync_queue'):
            logging.debug('Record was queued. Enabling.', record)
            self.rem_uid(uid, 'sync_queue')

        if self.has_uid(uid, 'sync_approve'):
            self.rem_uid(uid, 'sync_approve')

        if self.has_uid(uid, 'sync_error'):
            self.rem_uid(uid, 'sync_error')

        if self.has_uid(uid, 'sync_exclude'):
            logging.debug('Record already excluded', record)
            return False
        if len(record) > record_length:
            record = record[:record_length]
        self.add_record(record, 'sync_exclude')
        return True

    def delete_record(self, record):
        """Permanently remove data file corresponding to `record` from remote server"""
        uid = record[indexer.indexer.col_uid]
        r = self.server.storage.remove_uid(uid)
        logging.debug('Remove file result', uid, r)
        if self.has_uid(uid, 'sync_queue'):
            logging.debug('Record was queued. Enabling.', record)
            self.rem_uid(uid, 'sync_queue')

        if self.has_uid(uid, 'sync_approve'):
            self.rem_uid(uid, 'sync_approve')

        if self.has_uid(uid, 'sync_error'):
            self.rem_uid(uid, 'sync_error')

        if self.has_uid(uid, 'sync_exclude'):
            self.rem_uid(uid, 'sync_exclude')


    def collect(self, server=False):
        if not server:
            server = self.server
        if not server:
            logging.debug('StorageSync.collect: No remote storage defined')
            return 0
        all_tests = server.storage.list_tests()
        if all_tests is None:
            logging.error('StorageSync.collect: Impossible to retrieve remote storage list.')
            return 0
        
        def already_downloaded(uid):
            r = self.maindb.searchUID(uid, full=True)
            return r and os.path.exists(r[0])

        not_downloaded_tests = [
            test for test in all_tests if not already_downloaded(test[2])
        ]

        not_processed_tests = [
            test for test in not_downloaded_tests
            if not self.has_uid(test[2], 'sync_queue')
            and not self.has_uid(test[2], 'sync_exclude')
            and not self.has_uid(test[2], 'sync_error')
            and not self.has_uid(test[2], 'sync_approve')
        ]

        map(lambda record: self.add_record(record, 'sync_approve'),
            not_processed_tests)

        return len(not_processed_tests)

    def __len__(self):
        """Returns the length of the approval queue"""
        if not self.server:
            return 0
        return self.db.tab_len('sync_approve')




class SyncTable(QtGui.QTableView):

    """Table showing queued sync files, allowing the user to interact with them"""
    length = 0
    downloadRecord = QtCore.pyqtSignal(object)
    excludeRecord = QtCore.pyqtSignal(object)
    deleteRecord = QtCore.pyqtSignal(object)

    def __init__(self, dbpath, table_name, parent=None):
        super(SyncTable, self).__init__(parent)
        self.model_reference = SyncTableModel(
            indexer.Indexer(dbpath + '.sync'), table_name)
        self.setModel(self.model_reference)
        for i in (0, 6, 9, 11):
            self.hideColumn(i)
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.menu = QtGui.QMenu(self)
        if table_name.endswith('_approve'):
            self.menu.addAction(_('Download'), self.download)
            self.menu.addAction(_('Ignore'), self.exclude)
            self.menu.addAction(_('Delete'), self.delete)
        elif table_name.endswith('_queue'):
            self.menu.addAction(_('Ignore'), self.exclude)
        elif table_name.endswith('_exclude'):
            self.menu.addAction(_('Download'), self.download)
            self.menu.addAction(_('Delete'), self.delete)
        elif table_name.endswith('_error'):
            self.menu.addAction(_('Retry'), self.download)
            self.menu.addAction(_('Ignore'), self.exclude)
            self.menu.addAction(_('Delete'), self.delete)
        self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'),
                     self.showMenu)

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))

    def showEvent(self, ev):
        """Automatically switch to appropriate queue when showed"""
        self.model().select()
        return super(SyncTable, self).showEvent(ev)

    def __len__(self):
        """Returns the number of rows of the current table for the connected server serial"""
        n = self.model().rowCount()
        if n != self.length:
            self.model().select()
            self.length = n
        return n


    def download(self):
        for record in database.iter_selected(self):
            self.downloadRecord.emit(record)
        self.model().select()

    def exclude(self):
        """Move selection to sync_exclude table"""
        for record in database.iter_selected(self):
            self.excludeRecord.emit(record)
        self.model().select()

    def delete(self):
        """Delete selected records from remote server"""
        for record in database.get_delete_selection(self):
            self.deleteRecord.emit(record)
        self.model().select()


class SyncWidget(QtGui.QTabWidget):

    """Allows the user to control sync behavior."""
    ch = QtCore.pyqtSignal()
    dbpath = False

    def __init__(self, parent=None):
        super(SyncWidget, self).__init__(parent)
        self.transfer = TransferThread(parent=self)
        # Set local tasks manager
        if parent:
            self.transfer.set_tasks(parent.tasks)

        self.storage_sync = StorageSync(self.transfer)
        dbpath = confdb['database']
        # Create if missing
        try:
            db = indexer.Indexer(dbpath)
            db.close()
            db2 = indexer.Indexer(dbpath + '.sync')
            db2.close()
        except:
            logging.info(
                'Cannot set local db for storage sync \n%', format_exc())
            return
        self.dbpath = dbpath

        approve_sync_table = self.tab_approve = self.add_sync_table('sync_approve',
                                                                    _('Waiting approval'))

        def check_for_new_downloads():
            self.storage_sync.collect()
            approve_sync_table.model().select()

        approve_sync_table.menu.addAction(_('Check for new downloads'), check_for_new_downloads)

        self.tab_error = self.add_sync_table('sync_error', _('Errors'))
        self.tab_exclude = self.add_sync_table('sync_exclude', _('Ignored'))


    def add_sync_table(self, table_name, title):
        obj = SyncTable(self.dbpath, table_name, parent=self)
        self.addTab(obj, title)
        obj.downloadRecord.connect(self.storage_sync.download_record)
        obj.excludeRecord.connect(self.storage_sync.exclude_record)
        obj.deleteRecord.connect(self.storage_sync.delete_record)
        return obj

    def set_server(self, server):
        if not self.dbpath:
            return
        self.storage_sync.prepare(self.dbpath, server)
        serial = "serial='{}'".format(server['eq_sn'])
        self.tab_approve.model().setFilter(serial)
        self.tab_error.model().setFilter(serial)
        self.tab_exclude.model().setFilter(serial)

    def __len__(self):
        """Returns the length of the approval queue"""
        if not self.dbpath:
            return 0
        n = len(self.tab_approve)
        return n

    def showEvent(self, ev):
        """Automatically switch to appropriate queue when showed"""
        r = super(SyncWidget, self).showEvent(ev)
        if not self.dbpath:
            return r
        if len(self.tab_approve):
            if self.currentIndex() != 0:
                self.setCurrentIndex(0)
        elif len(self.tab_error):
            if self.currentIndex() != 2:
                self.setCurrentIndex(2)
        return r
