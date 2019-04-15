#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest

from misura.client import filedata
from misura.client.clientconf import confdb
from misura.client.tests import iutils_testing

# Needed for doc creation to work! (must register widgets)
import veusz.document as document
import veusz.widgets

from misura.client.flash import flashline
from misura.client.flash.flashline import convert

from misura.client.flash.flashline.tests import testdir

#test_path = '/home/daniele/Sviluppo/thegram/1322MOshinythin/TestInformation.xml'
#segment = 'T100'
test_path = testdir + 'TestInformation.xml'
segment = 'T400'

#test_path = '/home/daniele/Sviluppo/thegram/813/TestInformation.xml'
#test_path = 'D:\Sviluppo/thegram/1273MO/TestInformation.xml'

T400_clarkTaylor1s = [[('Start time of the shot', 'Float'), 
                       ('Temperature', 'Float'),
                       ('Clark&Taylor(1)', 'Float')], 
                      [6448.0, 383.0, 0.4317], [6589.0, 383.0, 0.4322], [6734.0, 384.0, 0.4314]]

smp_clarkTaylor1s = [[('Shooting start time', 'Float'), 
                      ('Temperature', 'Float'),
                      ('Clark&Taylor(1)', 'Float'), 
                      ('Clark&Taylor(1) Error', 'Float'),
                      ('Setpoint', 'Float')], 
                    [6448.0, 383.3333333333333, 0.43176665902137756, 0.00032998977]]


rule_inc = '/flash/sample1/clarkTaylor1s$\n/flash/sample1/{0}/clarkTaylor1s'.format(
    segment)


class TestConverter(unittest.TestCase):

    def test(self):
        from misura.client import confwidget
        confwidget.check_default_database = lambda *a, **k: True 
        cvt = flashline.Converter()
        itdb = confdb['flash_importToDb']
        confdb['flash_importToDb'] = False
        cvt.confdb = confdb
        #out = cvt.get_outpath(test_path)
        out = cvt.convert(test_path)
        confdb['flash_importToDb'] = itdb
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=out, rule_inc=rule_inc))
        doc = filedata.MisuraDocument()
        self.doc = doc
        imp.do(doc)
        # autoload

        d_len = len(doc.data['0:kiln/T'])
        self.assertGreater(d_len, 10)
        self.assertEqual(d_len, len(doc.data['0:t']))
        print('DATA', doc.data.keys())
        print('AVAIL', doc.available_data.keys())
        self.assertIn('0:flash/sample1/clarkTaylor1s', doc.data)
        self.assertIn(
            '0:flash/sample1/{}/N1/corrected'.format(segment), doc.available_data)
        ds = doc.data['0:flash/sample1/clarkTaylor1s']
        
        #self.assertEqual(len(ds.data), len(ds.serr))

        # no load: ds present but empty
        self.assertIn(
            '0:flash/sample1/{}/N1/raw'.format(segment), doc.available_data)
        self.assertNotIn('0:flash/sample1/{}/N1/raw'.format(segment), doc.data)

        dd = doc.data.keys() + doc.available_data.keys()
        self.assertNotIn('0:flash/sample1/clarkTaylor1sError', dd)
        self.assertNotIn('0:flash/sample1/clarkTaylor1sError_T', dd)
        self.assertNotIn('0:flash/sample1/clarkTaylor1sError_t', dd)

        c = imp.proxy.conf
        self.assertEqual(c.flash['mro'], ['Flash', 'Instrument'])
        self.assertEqual(c.flash.measure['mro'], ['MeasureFlash', 'Measure'])
        kilnT = self.doc.data['0:kiln/T'].data
        t0 = c.flash.measure['zerotime']
        self.assertAlmostEqual(kilnT[int(1447284799 - t0)], 382.8)
        self.assertAlmostEqual(kilnT[int(1447284822 - t0)], 382.8)
        
        self.check_aggregations(c.flash.sample1)
        
        self.check_summary_table(c.flash.sample1.describe(), ['celsius', 'second', 'second', 'second', 'second'], 
                                 [1, 5, 5, 5, 5])
        self.check_summary_table(c.flash.describe(), ['celsius', 'second', 'second', 'cm^2/second', 'cm^2/second'], 
                                 [0, 4, 4, 4, 4])
        # Check option values
        self.assertAlmostEqual(
            c.flash.sample1.T400.N1['clarkTaylor1'], 0.4317, delta=0.0001)
        self.assertAlmostEqual(
            c.flash.sample1.T400.N2['clarkTaylor1'], 0.4322, delta=0.0001)
        self.assertAlmostEqual(
            c.flash.sample1.T400.N3['clarkTaylor1'], 0.4314, delta=0.0001)

        self.assertAlmostEqual(
            c.flash.sample1.T400['clarkTaylor1'], 0.43176111578941345)
        self.assertAlmostEqual(
            c.flash.sample1.T400['clarkTaylor1Error'], 0.0003216423)
        self.assertEqual(
            c.flash.sample1.T400['clarkTaylor1s'][0], T400_clarkTaylor1s[0])
        for i in range(1, 4):
            self.assertAlmostEqual(
                c.flash.sample1.T400['clarkTaylor1s'][i][2], T400_clarkTaylor1s[i][2], delta=0.0001)
        self.assertEqual(
            c.flash.sample1['clarkTaylor1s'][0], smp_clarkTaylor1s[0])
        self.assertAlmostEqual(
            c.flash.sample1['clarkTaylor1s'][1][2], smp_clarkTaylor1s[1][2], delta=0.0001)
        self.assertAlmostEqual(
            c.flash.sample1['clarkTaylor1s'][1][3], smp_clarkTaylor1s[1][3], delta=0.0001)

        self.check_results_tables(c.flash.sample1.describe(), 
                                  ['second', 'celsius', 'cm^2/second', 'cm^2/second', 'celsius'],
                                  [2, 1, 5, 5, 1])

    def check_aggregations(self, smp):
        seg = getattr(smp, segment)
        tab = seg['clarkTaylor1s'][1:]
        segment_values = self.doc.data[
            '0:flash/sample1/{}/clarkTaylor1s'.format(segment)].data
        segment_times = self.doc.data[
            '0:flash/sample1/{}/clarkTaylor1s_t'.format(segment)].data
        segment_Ts = self.doc.data[
            '0:flash/sample1/{}/clarkTaylor1s_T'.format(segment)].data
        for i in range(3):
            shot = getattr(seg, 'N{}'.format(i + 1))
            self.assertEqual(shot['time'], tab[i][0])
            self.assertEqual(shot['temperature'], tab[i][1])
            self.assertEqual(shot['clarkTaylor1'], tab[i][2])

            self.assertEqual(shot['time'], segment_times[i])
            self.assertEqual(shot['temperature'], segment_Ts[i])
            self.assertEqual(shot['clarkTaylor1'], segment_values[i])
        self.check_summary_table(smp.describe(), 
                                 ['celsius', 'second', 'second', 'second', 'second'],
                                 [1, 5, 5, 5, 5])
        self.assertEqual(len(smp['summary']), 2)

    def test_add_results_tables(self):
        out = {}
        convert.add_results_tables(out, confdb, with_errors=False)
        self.assertTrue(out.has_key('clarkTaylor1s'))
        self.assertEqual(
            out['clarkTaylor1s']['unit'], ['second', 'celsius', 'cm^2/second'])
        self.assertEqual(out['clarkTaylor1s']['precision'], [0, 1, 4])
        self.assertFalse(out.has_key('clarkTaylor1sError'))
        self.assertFalse(out['clarkTaylor1s'].has_key('error'))

        out = {}
        convert.add_results_tables(out, confdb,  with_errors=True)
        self.check_results_tables(out, 
                                  ['second', 'celsius', 'cm^2/second', 'cm^2/second'],
                                  [0, 1, 4, 4])

    def check_results_tables(self, out, chk_units, chk_precision):
        self.assertTrue(out.has_key('clarkTaylor1s'))
        self.assertEqual(out['clarkTaylor1s']['unit'], chk_units)
        self.assertEqual(out['clarkTaylor1s']['precision'], chk_precision)
        self.assertTrue(out.has_key('clarkTaylor1sError'))
        self.assertEqual(out['clarkTaylor1s']['error'], 'clarkTaylor1sError')
        self.assertEqual(out['clarkTaylor1s']['precision'], chk_precision)

        self.assertEqual(out['clarkTaylor1sError']['unit'], 'cm^2/second')
        self.assertEqual(out['clarkTaylor1sError']['precision'], 4)

    def test_add_summary_table(self):
        out = {}
        convert.add_summary_table(out, with_errors=True)
        self.check_summary_table(out,['celsius', 'second', 'second', 'cm^2/second', 'cm^2/second'], [0, 4, 4, 4, 4])

    def check_summary_table(self, out, expect, precision):
        self.assertTrue(out.has_key('summary'))
        print(out['summary'])
        self.assertEqual(
            out['summary']['unit'][:5], expect)
        self.assertEqual(out['summary']['precision'][:5], precision)
        


if __name__ == "__main__":
    unittest.main(verbosity=2)
