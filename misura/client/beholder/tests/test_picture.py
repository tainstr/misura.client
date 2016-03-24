#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests camera ViewerPicture"""
import unittest
from nose.plugins.skip import SkipTest

import functools
from misura.client.tests import iutils_testing

from misura.client.beholder import picture

@SkipTest #Needs the server, so it should not be run automatically
class ViewerPicture(unittest.TestCase):

    def setUp(self):
        from misura.beholder import sim_camera

        fix_me = None
        self.server = fix_me
        self.rem = sim_camera.SimCamera(parent=self.server)
        self.rem.start_acquisition = functools.partial(
            self.server.set, 'isRunning', True)
        self.rem.parent = lambda: self.server
        self.obj = picture.ViewerPicture(self.rem, self.server)
        self.rem.copy = lambda: self.rem

    def tearDown(self):
        self.obj.close()

    def test_init(self):
        sz = self.rem['size']
        self.assertEqual(self.obj.plane.box.rect().width(), sz[0])
        self.assertEqual(self.obj.plane.box.rect().height(), sz[1])

if __name__ == "__main__":
    unittest.main()
