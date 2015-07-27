#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.row module."""
import unittest
import os
from misura.client import filedata
from misura.client import fileui
from misura.client.tests import iutils_testing
from veusz import widgets  # needed for document creation!
from PyQt4 import QtGui


class RowView(unittest.TestCase):

    def test_set_doc(self):
        fpath = os.path.join(iutils_testing.data_dir, 'test_video.h5')
        rv = fileui.RowView()
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=fpath))
        doc = filedata.MisuraDocument()
        imp.do(doc)

        rv.set_doc(doc)
        rv.set_idx(1)

        # FIXME: fix these functions!
        # logging.debug('%s %s', 'devmenu', rv.devmenu)
        # logging.debug('%s %s', 'header', rv.model().header)
        # logging.debug('%s %s', 'tree', rv.model().tree)


if __name__ == "__main__":
    unittest.main()
