#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import thegram.flashline.dataparser as dataparser
from thegram.flashline.tests import testdir

#testdir = '/home/daniele/Sviluppo/thegram/1273MO/'
# testdir = 'D:\Sviluppo/thegram/1273MO\'
test_path = testdir + 'TestInformation.xml'
smp_path = testdir + 'MO6_1'


class DataParser(unittest.TestCase):

    def test_parse_channel(self):
        data, header = dataparser.channel(testdir + 'MO6_1/00101001.fw0')
        self.assertEqual(len(data), 370038)
        if __name__ == "__main__":
            import pylab
            pylab.plot(range(len(data)), data)
            pylab.show()

    def test_parameters(self):
        info = dataparser.parameters(testdir + 'TestInformation.xml')
        self.assertIn('DateData', info)
        self.assertEqual(info['TestID']['__data__'][0], '1273MO')

    def test_acquisition_rate(self):
        rate, channels = dataparser.acquisition_rate(testdir + 'MO6_1/00101001.rat')
        self.assertEqual(rate, 30000)
        self.assertEqual(channels, 2)

    def test_debug_table(self):
        dataparser.debug_table(testdir + 'dta/1273MO.d_t')

    def test_sample_folder(self):
        segments, shots, results_table = dataparser.sample_folder(smp_path)
        self.assertEqual(len(segments),1)
        self.assertEqual(len(shots),1)
        self.assertEqual(len(shots[0]),3)

    def test_columns(self):
        info = dataparser.parameters(test_path)
        samples = dataparser.columns(info)
        self.assertEqual(len(samples[0]), 3)
        # First sample (0), Shots data (0), First segment (1), First shot (0)
        shot = samples[0][1][0][0]
        self.assertIn('header', shot)
        self.assertIn('fw0', shot)
        self.assertIn('fw1', shot)

        
if __name__ == "__main__":
    unittest.main(verbosity=2)
