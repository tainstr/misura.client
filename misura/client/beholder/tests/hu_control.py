#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests camera ViewerControl"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import unittest
#from misura import utils_testing as ut

from misura.client.beholder import control
from misura.beholder import sim_camera
from misura.morla import sim_motor
from misura.client import widgets

from misura.microscope import Hsm
from misura.flex import Flex
from PyQt4 import QtGui

# TODO: test if just one coordinate!

logging.debug('Importing', __name__)


def setUpModule():
    logging.debug('setUpModule', __name__)
    #ut.parallel(1)


def tearDownModule():
    logging.debug( 'Quitting app')
    #ut.parallel(0)
    logging.debug('tearDownModule', __name__)


class ViewerControl(unittest.TestCase):
    N = 1

    def setUp(self):
        self.root = None#ut.dummyServer(Hsm)
        instr = self.root.hsm
        instr['nSamples'] = self.N
        self.rem = sim_camera.SimCamera(parent=self.root)
# 		self.rem.encoder['react']='Strictly Follow'
        self.rem.encoder['react'] = 'No Follow'
        self.rem.create_video()
        enc = self.rem.encoder
        enc['invert'] = -1
# 		enc['react']='No Follow'
        vid = self.rem.videoObj
        cam = self.rem
        cam['resolution'] = (1280, 760)
        cam['nSamples'] = self.N
        cam['template'] = 'Hsm:%i' % self.N
        cam.desc.set('xPos', 2500)
        cam.desc.set('yPos', 2500)
        vid.init_pos(2500, 2500)
        cam.desc.set('xAlign', 1)
        cam.desc.set('yAlign', 1)
        vid.init_align(1, 1)
        self.motH = sim_motor.SimMotor(parent=self.root, node='motH')
        self.motH['steps'] = 5000
        self.motH['position'] = 2500
        self.motV = sim_motor.SimMotor(parent=self.root, node='motV')
        self.motV['steps'] = 5000
        self.motV['position'] = 2500
        self.motF = sim_motor.SimMotor(parent=self.root, node='motF')
        self.motF['steps'] = 5000
        self.motF['position'] = 2500
        self.motA = sim_motor.SimMotor(parent=self.root, node='motA')
        self.motA['steps'] = 5000
        self.motA['position'] = 2500

        enc.x['motor'] = [self.motH['fullpath'], 'default', False]
        enc.x['align'] = 1
        enc.x.motor.setattr(
            'streamerPos', 'options', [self.rem['fullpath'], 'default', 'xPos'])

        enc.y['motor'] = [self.motV['fullpath'], 'default', False]
        enc.y['align'] = 1
        enc.y.motor(
            'streamerPos', 'options', [self.rem['fullpath'], 'default', 'yPos'])

        enc.focus['motor'] = [self.motF['fullpath'], 'default', False]
        enc.angle['motor'] = [self.motA['fullpath'], 'default', False]

        for s in range(self.N):
            smp = getattr(instr, 'sample%i' % s)
            self.rem['smp%i' % s] = [smp['fullpath'], 'default', False]
        self.obj = control.ViewerControl(self.rem, self.root)

    def tearDown(self):
        self.obj.close()

    @unittest.skip('')
    def test_init(self):
        sz = self.rem['size']
        self.assertEqual(self.obj.viewer.pix_width, sz[0])
        self.assertEqual(self.obj.viewer.pix_height, sz[1])

    def check_control(self, name, wg, tooltip=''):
        return
        obj = self.obj
        self.assertEqual(obj.controls[name], wg)
        pos = obj.positions[name]
        ql = obj.layout.itemAtPosition(*pos)
        self.assertEqual(ql.widget(), wg)
        self.assertEqual(wg.toolTip(), tooltip)

    def test_setControl(self):
        obj = self.obj
        wg = widgets.aNumber(self.root, self.motH, self.motH.gete('goingTo'))
        obj.setControl(wg, 'bottom', 'tooltip')
        self.check_control('bottom', wg)
        wg1 = widgets.aNumber(self.root, self.motV, self.motV.gete('goingTo'))
        obj.setControl(wg1, 'left', 'tooltip1')
        self.check_control('left', wg1)

        obj.show()
        appQtGui.qApp.exec_()

        obj.delControl('left')
        self.assertEqual(obj.controls['left'], None)

        obj.delControls()
        self.assertEqual(obj.controls.values(), [None] * 4)


if __name__ == "__main__":
    unittest.main()
