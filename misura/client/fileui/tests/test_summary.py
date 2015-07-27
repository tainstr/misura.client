#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests summary table"""
import unittest
import os

from misura.client.tests import iutils_testing
from misura.client.fileui import SummaryView
from misura.client import filedata, plugin  # neeeded for correct veusz init!

from PyQt4 import QtGui

nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')


class TestSummary(unittest.TestCase):

    def setUp(self):
        self.s = SummaryView()

    def test(self):
        doc = filedata.MisuraDocument(nativem4)
        doc.reloadData()
        self.s.set_doc(doc)

        iutils_testing.show(self.s, __name__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
