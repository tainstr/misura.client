#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import os
from misura.canon.logger import Log as logging

from misura.client.tests import iutils_testing
from misura import parameters as params
from misura.canon.indexer import SharedFile
from misura.client import video
import shutil
from PyQt4 import QtGui


class Video(unittest.TestCase):

    def setUp(self):
        self.test_file = os.path.join(iutils_testing.data_dir, 'video_file.h5')
        self.source_file = os.path.join(
            iutils_testing.data_dir, 'test_video.h5')
        self.output_file_name = os.path.join(
            iutils_testing.data_dir, 'output.avi')

        self.clean()
        shutil.copy(self.source_file, self.test_file)

    def tearDown(self):
        self.clean()

    @unittest.skipIf(__name__ != '__main__', 'Not interactive')
    def test_gui(self):
        shared_file = SharedFile(self.test_file)
        video_exporter = video.VideoExporter(shared_file)
        video_exporter.show()
        QtGui.qApp.exec_()
        shared_file.close()

    @unittest.skip('frame is not preset in tests files at the moment')
    def test_export_image(self):
        shared_file = SharedFile(self.test_file, '/hsm/sample0/frame')
        self.output_file_name = os.path.join(
            iutils_testing.data_dir, 'output.avi')
        video.export(shared_file, output=self.output_file_name)

        shared_file.close()

        self.assertTrue(os.path.exists(self.output_file_name))

    def test_export_profile(self):
        shared_file = SharedFile(self.test_file)

        self.assertFalse(os.path.exists(self.output_file_name))

        video.export(
            shared_file, '/hsm/sample0/profile', output=self.output_file_name)
        shared_file.close()

        self.assertTrue(os.path.exists(self.output_file_name))

    def clean(self):
        iutils_testing.silent_remove(self.test_file)
        iutils_testing.silent_remove(self.output_file_name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
