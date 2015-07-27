#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the ShapesPlugin."""
import unittest
import os
import veusz.document as document

from misura.client.tests import iutils_testing as iut
from misura.client import filedata

from misura.client import plugin


class ShapesPlugin(unittest.TestCase):

    """Tests the CalibrationPlugin"""

    def do(self, doc, target):
        fields = {'sample': target, 'temp': True, 'time': True, 'text':
                  '$shape$\\\\%(xlabel)s=%(x)i', 'currentwidget': '/temperature/temp'}
        shapesPlugin = plugin.ShapesPlugin()
        shapesPlugin.apply(self.cmd, fields)

    def test(self):
        """Double import a file and subtract the same datasets."""
        nativem4 = os.path.join(iut.data_dir, 'test_video.h5')
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=nativem4))
        misuraDocument = filedata.MisuraDocument()
        self.cmd = document.CommandInterface(misuraDocument)
        plugin.makeDefaultDoc(self.cmd)
        imp.do(misuraDocument)
        # Import again
        imp.do(misuraDocument)
        misuraDocument.model.refresh()
        tree = misuraDocument.model.tree
        entry = tree.traverse('0:hsm/sample0')

        self.assertTrue(entry != False)

        self.do(misuraDocument, entry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
