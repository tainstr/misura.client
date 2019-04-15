#!/usr/bin/python
# -*- coding: utf-8 -*-
"""LICENSING NOTICE
This file should not be distributed in source nor byte-compiled form.
This file imports GPL libraries and thus, it must be considered an internal, unreleased software tool.
"""
import unittest
from time import sleep
import os

from misura.client import filedata
from misura.client.tests import iutils_testing

# Needed for doc creation to work! (must register widgets)
import veusz.document as document
import veusz.widgets

from misura.client import plugin  # Force wrapping of thegram plugins

from thegram.plugin.tests import testdir
from thegram.plugin.TwoLayers import TwoLayersPlugin

nativem4 = testdir + '../../flashline/tests/data/1273MO.h5'


class TestTwoLayersPlugin(unittest.TestCase):

    """Tests the TwoLayers plugin"""
    
    def setUp(self):
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=nativem4, rule_load='sample1/T400/N1'))
        self.doc = filedata.MisuraDocument()
        self.cmd = document.CommandInterface(self.doc)
        plugin.makeDefaultDoc(self.cmd)
        imp.do(self.doc)
        self.shot_path = '0:flash/sample1/T400/N1'
        self.assertIn(self.shot_path + '/raw', self.doc.data)
        self.doc.model.refresh()
        self.shot_node = self.doc.model.tree.traverse(self.shot_path)
        self.shot_conf = self.shot_node.get_configuration()
        self.p = TwoLayersPlugin()
        
    def check_cache(self):
        self.assertIn(self.shot_path + '/twolayers/theory', self.doc.cache)
        self.assertIn(self.shot_path + '/twolayers/residuals', self.doc.cache)
        self.assertIn(self.shot_path + '/twolayers/theory_t', self.doc.cache.keys()+self.doc.data.keys())
        self.assertIn(self.shot_path + '/corrected', self.doc.data)
        self.assertIn(self.shot_path + '/corrected_t', self.doc.data)       

    def _test(self, nosync=True):
        fields = {'root': self.shot_node, 'silent': True, 'nosync': nosync}
        self.p.apply(self.cmd, fields)
        
        while len(self.doc.plugin_process)>0:
            sleep(1)
        
        self.check_cache()
        self.check_doc()
        
    def check_doc(self):
        self.doc.model.refresh(force=True)
        out_node = self.doc.model.tree.traverse(self.shot_path+'/twolayers')
        self.assertTrue(out_node)
        out_conf = out_node.get_configuration()
        self.shot_node = self.doc.model.tree.traverse(self.shot_path)
        self.shot_conf = self.shot_node.get_configuration()
        self.assertEqual(out_conf['ml2_diffusivity1'], 
                         self.shot_conf['ml2_diffusivity1'])
        self.assertEqual(out_conf['ml2_diffusivity2'], 
                         self.shot_conf['ml2_diffusivity2'])
        # Check aggregates
        segment_conf = self.shot_node.parent.get_configuration()
        self.assertEqual(len(segment_conf['twolayers1']), 4)
        self.assertEqual(segment_conf['twolayers1'][1][2], 
                         out_conf['ml2_diffusivity1'])
        self.assertEqual(segment_conf['twolayers1'][2][2], None)
        self.assertEqual(segment_conf['twolayers1'][3][2], None)
        self.assertEqual(len(segment_conf['twolayers2']), 4)
        self.assertEqual(segment_conf['twolayers2'][1][2], 
                         out_conf['ml2_diffusivity2'])
        self.assertEqual(segment_conf['twolayers2'][2][2], None)
        self.assertEqual(segment_conf['twolayers2'][3][2], None)
        sample_conf = self.shot_node.parent.parent.get_configuration()
        self.assertEqual(len(sample_conf['twolayers1']), 2)
        self.assertEqual(len(sample_conf['twolayers2']), 2) 
        
    def test_async(self):
        self._test() 
        
    def test_sync(self):
        self._test(False)
        
    def test_parallel(self):
        fields = {'root': self.shot_node, 'silent': True, 'nosync': False}
        self.p.pre_apply(self.cmd, fields, parallel=True)
        self.assertTrue(self.p.params_pickle)
        self.assertTrue(os.path.exists(self.p.params_pickle))
        self.p.do()
        self.assertFalse(self.p.params_pickle)
        self.p.post_process()
        self.check_cache()
        self.check_doc()
        


if __name__ == "__main__":
    unittest.main(verbosity=2)
