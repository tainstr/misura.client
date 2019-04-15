#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import unittest

from thegram.flashline import cdv
from thegram.flashline.tests import testdir

smp_path = os.path.join(testdir, 'MO6_1')
cdv1_path = os.path.join(smp_path, '00101001.cdv')
cdv2_path = os.path.join(smp_path, '00101002.cdv')
cdv3_path = os.path.join(smp_path, '00101003.cdv')

ipJ_path = os.path.join(testdir, '00102001.ipj')
ipR_path = os.path.join(testdir, '00102001.ipr')

class TestCDV(unittest.TestCase):

    def test_read_cdv_struct(self):
        s = cdv.CDV.open(cdv3_path)
        self.assertAlmostEqual(s.furnace_temp, 383.5)
        self.assertEqual(len(s._values), 500)
        self.assertEqual(s.segment, 1)
        self.assertEqual(s.sample, 1)
        self.check(s)
        self.assertEqual(
            s.values['calc_clark_and_taylor_r1'], 0.43142226338386536)
        self.assertEqual(
            s.values['calc_clark_and_taylor_r2'], 0.4318832755088806)
        self.assertEqual(
            s.values['calc_clark_and_taylor_r3'], 0.43532443046569824)

        s = cdv.CDV.open(cdv1_path)
        self.assertAlmostEqual(s.furnace_temp, 382.79998779)
        self.check(s)
        s = cdv.CDV.open(cdv2_path)
        self.assertAlmostEqual(s.furnace_temp, 383.200012207)
        self.check(s)

    def check(self, s):
        self.assertAlmostEqual(s.values['c_software_version'], 
                               15.14, delta=0.0001)
        self.assertEqual(s.diffusivity, s.values['calc_clark_and_taylor_avg'])
        self.assertAlmostEqual(s.values['calc_clark_and_taylor_avg'], 
                               (s.values['calc_clark_and_taylor_r1'] +
                                s.values['calc_clark_and_taylor_r2'] +
                                s.values['calc_clark_and_taylor_r3']) / 3)
        
class TestGenericKeyValueResultFile(unittest.TestCase):
    R_equals_J =('Baseline', 'Slope', 'Paramm', 'T_max', 'Temperature', 'Thickness', 
         'Radius', 'IrradiatedRadiusInner', 'IrradiatedRadiusOuter', 'ViewedRadius')
    
    def test_read_ipj_ipr(self):
        ipJ = cdv.GenericKeyValueResultFile.open(ipJ_path)
        ipR = cdv.GenericKeyValueResultFile.open(ipR_path)
        
        for k in self.R_equals_J:
            self.assertEqual(ipJ[k], ipR[k])
