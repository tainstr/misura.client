#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests single-file simplified Plot"""
import unittest

import os
from misura.client.tests import iutils_testing
from misura.client.graphics import Plot
from misura.client import filedata
from misura.client.navigator import Navigator
from PyQt4 import QtGui, QtCore


nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')


class TestPlot(unittest.TestCase):

    def setUp(self):
        self.p = Plot()
        self.nav = Navigator()
        self.nav.connect(
            self.p, QtCore.SIGNAL('hide_show(QString)'), self.nav.plot)

    @unittest.skipIf(__name__ != '__main__', "should be executed only manually")
    def test(self):
        doc = filedata.MisuraDocument(nativem4)
        doc.reloadData()
        self.p.set_doc(doc)
        self.nav.set_doc(doc)
        self.p.updateCurvesMenu()
        self.p.updateCurveActions()
        self.p.hide_show('0:hsm/sample0/Vol')

        iutils_testing.show(self.p, __name__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
