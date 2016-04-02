#!/usr/bin/python
# -*- coding: utf-8 -*-
"""misura Configuration Manager"""
import unittest
from misura.client.tests import iutils_testing
from misura.client import clientconf, confwidget
import tempfile
from PyQt4 import QtGui


def temporary_filename():
    temporary_file = tempfile.NamedTemporaryFile(delete=False)
    file_name = temporary_file.name
    temporary_file.close()
    return file_name


class Conf(unittest.TestCase):

    def test_create(self):
        file_name = temporary_filename()
        client_configuration = clientconf.ConfDb(file_name)

        k0 = set(clientconf.default_desc.keys())
        k1 = set(client_configuration.desc.keys())
        self.assertEqual(k0, k1)

    def test_save(self):
        file_name = temporary_filename()

        client_configuration = clientconf.ConfDb(path=file_name)
        client_configuration['lang'] = 'en'
        client_configuration.save()

        reloaded_clientconf = clientconf.ConfDb(file_name)

        self.assertEqual(reloaded_clientconf.path, file_name)
        self.assertEqual(reloaded_clientconf['lang'], 'en')

    def test_mem(self):
        p = temporary_filename()

        cf = clientconf.ConfDb(p)
        cf.mem('file', 'name1', 'path1')
        cf.mem_file('name2', 'path2')
        self.assertEqual(
            cf.recent_file, [['name1', 'path1'], ['name2', 'path2']])
        for i in range(10):
            cf.mem_file(str(i), str(i))
        self.assertEqual(cf.recent_file[7], ['5', '5'])
        cf.save()
        o = cf.recent_file[:]
        cf = clientconf.ConfDb(p)

        self.assertEqual(cf.recent_file, o)

    def test_unicode(self):
        f = tempfile.NamedTemporaryFile(delete=False)
        cf = clientconf.ConfDb(f.name)
        f.close()
        cf.mem_file(u'Vallourec - 126F3 80\xb0C/min 3x3',
                    '/home/daniele/tmp/gr/Vallourec - 126F3 80Cmin 3x3_00612S.h5')

    @unittest.skipIf(__name__ != '__main__', 'Interactive')
    def test_widget(self):
        cc = confwidget.ClientConf()
        cc.show()
        QtGui.qApp.exec_()


if __name__ == "__main__":
    unittest.main()
