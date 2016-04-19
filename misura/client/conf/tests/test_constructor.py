#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the programmatic widget construction."""
import unittest
import os
from misura.canon.option import ConfigurationProxy
from misura.client.conf import constructor
from misura.client import filedata
from misura.client.tests import iutils_testing

nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')


class TestConstructor(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_proxy = filedata.getFileProxy(nativem4)
        file_proxy.load_conf()
        file_proxy.close()       
        self.conf = file_proxy.conf
        
    def test_orgSections(self):
        sec = constructor.orgSections(self.conf.post.measure.describe())
        handles = [o['handle'] for o in sec['Main']]
        self.assertTrue('param_Sint' not in handles)
        
    def test_section(self):
        std = self.conf.post.measure
        sec = constructor.orgSections(std.describe())['Main']
        obj = constructor.Section(self.conf, std, sec)
        iutils_testing.show(obj, __name__)
    
    def test_interface(self):
        rem = self.conf.post.measure
        obj = constructor.Interface(self.conf, rem, rem.describe())
        iutils_testing.show(obj, __name__)
        
    def test_nested_options(self):
        p = ConfigurationProxy()
        p.add_option('a', 'String', '')
        p.add_option('b', 'String', '', parent='a')
        p.add_option('c', 'String', '', parent='b')
        p.add_option('sec_d', 'String', '')
        obj = constructor.Interface(p, p, p.describe())
        iutils_testing.show(obj, __name__)


if __name__ == "__main__":
    unittest.main()
