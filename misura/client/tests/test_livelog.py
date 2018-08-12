#!/usr/bin/python
# -*- coding: utf-8 -*-
"""misura Configuration Manager"""
import unittest
from misura.client.tests import iutils_testing
from misura.client import livelog
from misura.client.live import registry
from PyQt4 import QtGui, QtCore
log_colors = [(10,'black'), (20, 'black'), (30, 'blue'), (40, 'orange'), (50, 'red')]

class LiveLog(unittest.TestCase):

    def test_no_updates_when_log_is_unchanged(self):
        registry.log_buf = [1,2,3,4]
        log = livelog.LiveLog()
        log.current_buf = [1,2,3,4]

        log.slotUpdate()

        self.assertEquals([1,2,3,4], log.current_buf)

    def test_update(self):
        registry.log_buf = [1,2,3,4]
        log = livelog.LiveLog()
        log.current_buf = [1,2]

        log.slotUpdate()

        self.assertEquals([1,2], log.current_buf)
        
    def check_color(self, level, color, qcolor):
        name = QtGui.QColor(color).name()
        qname = qcolor.name()
        msg =  'Wrong color {} {}({})!={}'.format(level, color,name,qname)
        self.assertEqual(qname, name, msg) 
      
    def test_color_level(self):
        for level, color in log_colors:
            ret = livelog.color_level(level)
            self.check_color(level, color, ret)
    
    def test_decorate(self):
        for level, bold, italic in [(10, 0, 1), 
                (20, 0, 0), (30, 1, 0), (40, 1, 0), (50, 1, 0)]:
            brush = livelog.decorate(level, QtCore.Qt.FontRole)
            self.assertEqual(brush.bold(), bold)
            self.assertEqual(brush.italic(), italic)
        for level, color in log_colors:
            brush = livelog.decorate(level, QtCore.Qt.ForegroundRole)
            self.check_color(level, color, brush.color())

if __name__ == "__main__":
    unittest.main()
