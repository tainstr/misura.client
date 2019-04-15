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
from thegram.plugin.Gembarovic2D import Gembarovic2DPlugin

nativem4 = testdir + '../../flashline/tests/data/1273MO.h5'
shot_path = '0:flash/sample1/T400/N1'

#nativem4 = '/home/daniele/MisuraData/flash/540.h5'
#shot_path = '0:flash/sample1/T25/N5'

class TestGembarovic2DPlugin(unittest.TestCase):

    """Tests the Gembarovic2D plugin"""

    def setUp(self):
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=nativem4, rule_load=shot_path.split('flash/')[1]))
        self.doc = filedata.MisuraDocument()
        self.cmd = document.CommandInterface(self.doc)
        plugin.makeDefaultDoc(self.cmd)
        imp.do(self.doc)
        self.shot_path = shot_path
        self.assertIn(self.shot_path + '/raw', self.doc.data)
        self.doc.model.refresh()
        self.shot_node = self.doc.model.tree.traverse(self.shot_path)
        self.shot_conf = self.shot_node.get_configuration()
        self.p = Gembarovic2DPlugin()
        
    def test_pre_apply(self):
        self.p.pre_apply(self.cmd, {'root': self.shot_node, 'silent': True, 'nosync': False})
        self.assertTrue(self.p.pre_applied)
        self.assertGreater(self.p.configuration_proxy['jg2d_endTime'], 100)

    def check_cache(self):
        self.assertIn(self.shot_path + '/gembarovic/theory', self.doc.cache)
        self.assertIn(self.shot_path + '/gembarovic/residuals', self.doc.cache)
        self.assertIn(
            self.shot_path[:-3] + '/gembarovic_t', self.doc.cache.keys() + self.doc.data.keys())
        self.assertIn(self.shot_path + '/corrected', self.doc.data)
        self.assertIn(self.shot_path + '/corrected_t', self.doc.data)

    def _test(self, nosync=True):
        fields = {'root': self.shot_node, 'silent': True, 'nosync': nosync}
        self.p.apply(self.cmd, fields)

        while len(self.doc.plugin_process) > 0:
            sleep(1)

        self.check_cache()
        self.check_doc()

    def check_doc(self):
        self.doc.model.refresh(force=True)
        out_node = self.doc.model.tree.traverse(self.shot_path + '/gembarovic')
        self.assertTrue(out_node)
        out_conf = out_node.get_configuration()
        self.assertTrue(out_conf)
        self.assertEqual(out_conf['name'], u'Gembarovic2D at 382.8°C')
        self.assertEqual(out_conf['comment'], '')
        self.shot_node = self.doc.model.tree.traverse(self.shot_path)
        self.assertTrue(self.shot_node)
        shot_conf = self.shot_node.get_configuration()
        self.assertTrue(shot_conf)
        self.assertEqual(
            out_conf['jg2d_diffusivity'], shot_conf['jg2d_diffusivity'])
        self.assertAlmostEqual(out_conf['jg2d_diffusivity'], 0.4236, delta=1e-4)
        # Check aggregates
        segment_conf = self.shot_node.parent.get_configuration()
        tab = segment_conf['gembarovic']
        self.assertEqual(len(tab), 4)
        #First row, third cell should contain diff
        self.assertAlmostEqual(
            segment_conf['gembarovic'][1][2], 0.4236, delta=1e-4)
        # Third row, third cell should contain None as no value was calculated
        self.assertEqual(tab[3][2], None)
        # Check header
        self.assertEqual(len(segment_conf['gembarovic'][0]), 4)
        # Check sample conf
        sample_conf = self.shot_node.parent.parent.get_configuration()
        self.assertEqual(len(sample_conf['gembarovic']), 2)
        #self.assertEqual(sample_conf['gembarovic'][1][2], segment_conf['gembarovic'][1][2])

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
