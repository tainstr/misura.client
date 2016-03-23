#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the programmatic widget construction."""
import unittest
import os
from misura.client.conf import constructor
from misura.client import filedata
from misura.client.tests import iutils_testing

nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')


class TestConstructor(unittest.TestCase):

    def test_orgSections(self):
        file_proxy = filedata.getFileProxy(nativem4)
        file_proxy.load_conf()
        file_proxy.close()

        sec = constructor.orgSections(file_proxy.conf.post.measure.describe())
        handles = [o['handle'] for o in sec['Main']]

        self.assertTrue('param_Sint' not in handles)

    def test_section(self):
        file_proxy = filedata.getFileProxy(nativem4)
        file_proxy.load_conf()
        file_proxy.close()

        std = file_proxy.conf.post.measure
        sec = constructor.orgSections(std.describe())['Main']

        obj = constructor.Section(file_proxy.conf, std, sec)
        iutils_testing.show(obj, __name__)

    def test_interface(self):
        file_proxy = filedata.getFileProxy(nativem4)
        file_proxy.load_conf()
        file_proxy.close()

        rem = file_proxy.conf.post.measure
        obj = constructor.Interface(file_proxy.conf, rem, rem.describe())
        iutils_testing.show(obj, __name__)


if __name__ == "__main__":
    unittest.main()
