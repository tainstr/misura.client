#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing fileui.minimage module."""

import unittest
import os
from misura.client import filedata
from misura.client import fileui
from misura.client.tests import iutils_testing
from misura.canon import indexer
from veusz import widgets  # needed for document creation!
from PyQt4 import QtGui


@unittest.skip("there's a problem in travis when you try to write files in a test...")
class MiniImage(unittest.TestCase):

    def tearDown(self):
        iutils_testing.silent_remove(self.saved_file)

    def test_init(self):
        fpath = os.path.join(iutils_testing.data_dir, 'test_video.h5')

        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=fpath))
        doc = filedata.MisuraDocument()
        imp.do(doc)
        fp = indexer.SharedFile(fpath)
        decoder = filedata.DataDecoder()
        profile = '/hsm/sample0/profile'
        decoder.reset(fp, profile)

        self.sync(decoder)

        doc.decoders[profile] = decoder

        mini = fileui.MiniImage(doc, '/hsm/sample0/profile')
        mini.saveDir = iutils_testing.data_dir
        mini.set_idx(0)

        self.saved_file = mini.save_frame()
        self.assertTrue(os.path.exists(self.saved_file))

    def sync(self, decoder):
        self.assertGreater(decoder.get_len(), 0)
        decoder.cache(0)

if __name__ == "__main__":
    unittest.main()
