#!/usr/bin/python
# -*- coding: utf-8 -*-
"""LICENSING NOTICE
This file should not be distributed in source nor byte-compiled form.
This file imports GPL libraries and thus, it must be considered an internal, unreleased software tool.
""" 
import unittest

from misura.client import filedata
from misura.client.tests import iutils_testing

# Needed for doc creation to work! (must register widgets)
import veusz.document as document
import veusz.widgets

from misura.client import plugin # Force wrapping of thegram plugins

from  thegram.plugin.tests  import testdir
from thegram.plugin.Baseline import BaselinePlugin

nativem4 = testdir+'../../flashline/tests/data/1273MO.h5'


class TestBaselinePlugin(unittest.TestCase):

    """Tests the Baseline plugin"""
    
    def test(self):
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=nativem4, rule_load='sample1/T400/N1'))
        doc = filedata.MisuraDocument()
        self.cmd = document.CommandInterface(doc)
        plugin.makeDefaultDoc(self.cmd)
        imp.do(doc)
        shot_path = '0:flash/sample1/T400/N1'
        self.assertIn(shot_path+'/raw', doc.data)
        doc.model.refresh()
        shot_node = doc.model.tree.traverse(shot_path)
        fields = {'root': shot_node}
        p = BaselinePlugin()
        p.apply(self.cmd, fields)
        self.assertIn(shot_path + '/corrected', doc.data)
        self.assertIn(shot_path + '/corrected_t', doc.data)
        self.assertTrue(p.configuration_proxy.has_key('base_constant'))

if __name__ == "__main__":
    unittest.main(verbosity=2)
