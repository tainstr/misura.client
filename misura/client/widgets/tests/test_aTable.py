#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests aTable widget."""
import unittest
from misura.client.tests import iutils_testing

from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui, QtCore


class aTable(unittest.TestCase):

    def setUp(self):
        self.root = option.ConfigurationProxy()

    def wgGen(self):
        self.assertTrue(self.root.has_key('test'))
        widget = widgets.build(self.root, self.root, self.root.gete('test'))
        self.assertTrue(widget is not False)
        return widget

    def test(self):
        self.root.sete('test', option.ao({}, 'test', 'Table', [
                       [('ColStr', 'String'), ('ColInt', 'Integer'), ('ColFloat', 'Float')], 
                       ['pippo', 1, 0.5],
                       ['ciccio', 2, 1.5]])['test'])
        widget = self.wgGen()
        view = widget.table
        model = view.model()
        self.assertFalse(model.rotated)
        
        #Shape
        self.assertEqual(model.rowCount(), 2)
        self.assertEqual(model.columnCount(), 3)
        
        # Hor header
        self.assertEqual(model.headerData(0, QtCore.Qt.Horizontal),  'ColStr')
        self.assertEqual(model.headerData(1, QtCore.Qt.Horizontal),  'ColInt')
        self.assertEqual(model.headerData(2, QtCore.Qt.Horizontal),  'ColFloat')
        
        # The view should take care of column visibility
        self.assertTrue(model.visible_headers[0])
        model.set_visible_col(0, 0)
        self.assertEqual(model.columnCount(), 3)
        self.assertEqual(model.headerData(0, QtCore.Qt.Horizontal),  'ColStr')
        model.set_visible_col(0, 1)
        
        model.set_visible_row(0, 0)
        self.assertEqual(model.rowCount(), 2)
        # Nothing left
        self.assertEqual(model.headerData(0, QtCore.Qt.Vertical),  None)
        model.set_visible_row(0, 1)
        
        
        # Perp header
        self.assertEqual(model.headerData(0, QtCore.Qt.Vertical),  None)
        model.perpendicular_header_col = 0
        self.assertEqual(model.headerData(0, QtCore.Qt.Vertical),  'pippo')
        
        iutils_testing.show(widget, __name__)
        
        
    def test_rotation(self):
        rows = [['pippo'+str(i), i, i*100] for i in range(20)]
        tab = [[('ColStr', 'String'), ('ColInt', 'Integer'), ('ColFloat', 'Float')]]+rows
        self.root.sete('test', option.ao({}, 'test', 'Table', tab)['test'])
        widget = self.wgGen()
        view = widget.table
        model = view.model()
        self.assertFalse(model.rotated)
        
        # Check rotation
        model.rotated = False
        self.assertEqual(model.rowCount(), 20)
        print len(model.rows)
        self.assertEqual(model.columnCount(), 3)
        self.assertEqual(model.headerData(0, QtCore.Qt.Vertical),  None)
        model.perpendicular_header_col = 0
        self.assertEqual(model.headerData(0, QtCore.Qt.Vertical),  'pippo0')
        self.assertEqual(model.headerData(1, QtCore.Qt.Vertical),  'pippo1')
        
        self.assertEqual(model.headerData(0, QtCore.Qt.Horizontal),  'ColStr')
        self.assertEqual(model.headerData(1, QtCore.Qt.Horizontal),  'ColInt')
        self.assertEqual(model.headerData(2, QtCore.Qt.Horizontal),  'ColFloat')
        
        # Check rotation
        model.rotated = True
        self.assertEqual(model.rowCount(), 3)
        self.assertEqual(model.columnCount(), 20)
        
        self.assertEqual(model.headerData(0, QtCore.Qt.Horizontal),  'pippo0')
        self.assertEqual(model.headerData(1, QtCore.Qt.Horizontal),  'pippo1')
        
        self.assertEqual(model.headerData(0, QtCore.Qt.Vertical),  'ColStr')
        self.assertEqual(model.headerData(1, QtCore.Qt.Vertical),  'ColInt')
        self.assertEqual(model.headerData(2, QtCore.Qt.Vertical),  'ColFloat')       
        

if __name__ == "__main__":
    unittest.main(verbosity=2)
