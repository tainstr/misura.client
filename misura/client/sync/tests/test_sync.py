#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Database synchronization service and widget"""
import unittest
import os
import logging

from misura.canon import indexer
from misura.canon import option

from misura.client.tests import iutils_testing as iut

from misura.client import sync, determine_path
from misura.client.clientconf import ConfDb

PORT = 34987
# TODO: simple service

path = os.path.join(determine_path(__file__), 'data')
remote_dbdir = os.path.join(path, 'remote')
if not os.path.exists(remote_dbdir):
    os.makedirs(remote_dbdir)
remote_dbpath = os.path.join(remote_dbdir, 'remote_db.sqlite')

local_dbdir = os.path.join(path, 'local')
if not os.path.exists(local_dbdir):
    os.makedirs(local_dbdir)
local_dbpath = os.path.join(local_dbdir, 'local_db.sqlite')


test_confdb = os.path.join(path, 'conf_db.sqlite')
if os.path.exists(test_confdb):
    os.remove(test_confdb)
cdb = ConfDb(test_confdb)
cdb['database'] = test_confdb
# Monkey-patch confdb object in sync module, which was originally imported
# from clientconf.
sync.sync.confdb = cdb


logging.debug(remote_dbpath, local_dbpath)


class StorageSync(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        s = option.ConfigurationProxy()
        s.sete('isRunning', option.ao(
            {}, 'isRunning', 'Integer', 0)['isRunning'])
        s.sete('eq_sn', option.ao({}, 'eq_sn', 'String', 'test_sync')['eq_sn'])
        cls.srv = s  # base configuration proxy

        p = iut.FakeProxy(s)  # server proxy
        p.addr = 'https://127.0.0.1:{}/RPC'.format(PORT)
        p.storage = indexer.Indexer(remote_dbpath)
        cls.server = p
        cls.local = indexer.Indexer(local_dbpath)
        iut.enableSignalDebugging()

    def setUp(self):
        self.sync = sync.StorageSync()
        self.assertTrue(self.sync.prepare(test_confdb, self.server))

    def test_prepare(self):
        """Test object setup before thread start"""
        self.assertEqual(self.sync.serial, self.srv['eq_sn'])
        self.assertEqual(self.sync.remote_dbdir, remote_dbdir)
        self.assertEqual(self.sync.dbpath, test_confdb)

    def rec(self, i):
        row = indexer.indexer.testColumnDefault[:]
        i = str(i)
        row[:3] = ['file' + i, self.srv['eq_sn'], 'uid' + i]
        return row


    def test_collect(self):
        class FakeTransfer:
            def download_uid(*args):
                pass
            def start(self):
                pass

        r = self.sync.collect()
        print 'collect', r
        self.sync.transfer = FakeTransfer()
        r = self.sync.download_record(['a record', 'with', 'uid'])
        print 'download', r

    # TODO: these would need an https service
    def test_download(self):
        pass

    def test_download_record(self):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
