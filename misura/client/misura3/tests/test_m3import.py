#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Verify conversion from Misura3 to misura files. Windows-only unittest!"""
from misura.canon.logger import Log as logging
import unittest
import sys
import pickle

import tables
from tables.nodes import filenode

from misura.client import browser
from misura.client.misura3 import convert
from misura.client.conf import devtree
from misura.canon import reference
from misura.canon import indexer

from misura.client import filedata

from misura.client.tests import iutils_testing as iut


def setUpModule():
    if sys.platform not in ['win32', 'win64']:
        raise unittest.SkipTest(
            'Misura3->misura conversion is available only in windows platforms.')


hsm_names = set(['0:t', '0:hsm/sample0/ang', '0:hsm/sample0/A', '0:hsm/sample0/h', '0:hsm/sample0/eqhw', '0:hsm/sample0/soft', '0:hsm/sample0/w',
                 '0:kiln/P', '0:kiln/T', '0:kiln/S'])  # ,'/hsm/sample0/Width','/hsm/sample0/Softening'
hsmDoble_names = set(['0:t', '0:kiln/T', '0:hsm/sample0/Sint', '0:hsm/sample0/ang', '0:hsm/sample0/eqhw',
                      '0:hsm/sample0/A'])  # ,'/hsm/sample0/Width','/hsm/sample0/Softening'
dil_names = set(['0:t', '0:kiln/T', '0:horizontal/sample0/d', '0:kiln/S', '0:horizontal/sample0/camA',
                 '0:/horizontal/sample0/camB', '0:kiln/P', '0:horizontal/sample0/Mov'])
flex_names = set(['0:t', '0:kiln/T', '0:flex/sample0/d',
                  '0:kiln/S', '0:flex/sample0/camA', '0:kiln/P', '0:flex/sample0/Mov'])


class Convert(unittest.TestCase):

    """Verify conversion from Misura3 to Misura4 files. Windows-only!"""

    def check_logging(self, op):
        """Check length and content of log reference"""
        t = tables.openFile(op, mode='r')
        log = t.root.log[:]
        t.close()
        self.assertGreater(len(log), 4)
        # Decode first log line
        t, msg = reference.Log.decode(log[0])
        self.assertGreater(t,0)
        self.assertTrue(msg[1].startswith('Importing from'))

    def check_images(self, op, fmt='ImageM3', max_num = 10):
        """Check imported images"""
        print ' CHECK IMAGES'
        dec = filedata.DataDecoder()
        fp = indexer.SharedFile(op)
        dec.reset(proxy=fp, datapath='/hsm/sample0/frame')
        dec.ext = 'ImageM3' 
        t, img = dec.get_data(0)
        self.assertEqual(img.width(), 640)
        self.assertEqual(img.height(), 480)
        ofmt = fp.get_node_attr('/hsm/sample0/frame', 'type')

        N = fp.len('/hsm/sample0/frame')
        t, last_img = dec.get_data(N - 1)

        dec.close()
        fp.close()  # dec uses a copy of fp: must close both!

        self.assertTrue(img)
        self.assertEqual(fmt, ofmt)
        self.assertTrue(last_img)

    def check_import(self, op, names=False):
        """Simulate a data import operation"""
        logging.debug('%s %s', 'check_import', op)
        fp = indexer.SharedFile(op)
        fp.load_conf()
        rm = devtree.recursiveModel(fp.conf)
        fp.close()
        # Simulate an import
        imp = filedata.OperationMisuraImport(
            filedata.ImportParamsMisura(filename=op))
        doc = filedata.MisuraDocument()
        imp.do(doc)
        if names is not False:
            self.assertEqual(set(imp.outdatasets), names)
        return doc

    def check_standard(self, op):
        """Perform a re-standard"""
        # TODO: create test files with Width variable!
        fp = indexer.SharedFile(op)
        fp.load_conf()
        self.assertNotIsInstance(fp.conf.hsm.sample0['Sintering']['time'], basestring)
        fp.run_scripts(fp.conf.hsm)
        end = fp.col('/kiln/T',-1)
        self.assertEqual(fp.conf.hsm.measure['end']['time'], end[0])
        self.assertEqual(fp.conf.hsm.measure['end']['temp'], end[1])
        fp.close()
        
    def check_curve(self, op):
        """Check thermal cycle curve format"""
        fp = indexer.SharedFile(op)
        fp.load_conf()
        curve = fp.conf.kiln['curve']
        self.assertGreater(len(curve), 1)
        self.assertEqual(len(curve[0]), 2)
        fp.close()


#	@unittest.skip('')
    def test_0_data(self):
        """Conversion of data and configuration"""
        op = convert.convert(iut.db3_path, '00001S', force=True, keep_img=True, max_num_images = 10)
        self.assertTrue(op, 'Conversion Failed')
        t = tables.openFile(op, mode='r')
        n = filenode.openNode(t.root.conf)
        tree = pickle.loads(n.read())
        measure = tree['hsm']['measure']['self']
        self.assertEqual(measure['nSamples']['current'], 1)
        sumT = t.root.kiln.T
        nrows = len(sumT)
        inidim = getattr(
            t.root.hsm.sample0.h.attrs, 'initialDimension', None)
        t0 = sumT[0][0]
        T0 = sumT[0][1]
        h0 = t.root.hsm.sample0.h[0][1]
        log = t.root.log[:]
        t.close()
        self.check_standard(op)
#        self.check_logging(op)
#        self.check_import(op, hsm_names)
#        self.check_images(op,'Image')
#        self.check_curve(op)
#        self.assertEqual(nrows, max_num_images)
#        self.assertEqual(t0, 0.0)
#        self.assertEqual(T0, 361.0)
#        self.assertEqual(h0, 100.0)
        self.assertEqual(inidim, 3000)

    @unittest.skip('')
    def test_1_formats(self):
        # Test jpeg format
        op = convert.convert(
            iut.db3_path, '00001S', force=True, img=True, keep_img=False, format='jpeg')
        self.check_images(op, 'jpeg')
        # Test m3 format
        op = convert.convert(
            iut.db3_path, '00001S', force=True, img=True, keep_img=False, format='m3')
        self.check_images(op, 'm3')
        # Test m4 format
        op = convert.convert(
            iut.db3_path, '00001S', force=True, img=True, keep_img=False, format='m4')
        self.check_images(op, 'm4')

    @unittest.skip('')
    def test_2_noforce(self):
        op = convert.convert(iut.db3_path, '00001S', force=False, img=True)
        self.assertTrue(op)

    @unittest.skip('')
    def test_3_keepimg(self):
        op = convert.convert(
            iut.db3_path, '00001S', force=True, img=True, keep_img=True)
        self.assertTrue(op)

    @unittest.skip('')
    def test_8_importConverted(self):
        # Convert just data and conf
        op = convert.convert(iut.db3_path, '00001S', force=True, keep_img=True)
        self.assertTrue(op)
        doc = self.check_import(op, hsm_names)
        self.assertEqual(
            doc.data['0:hsm/sample0/h'].m_initialDimension, 3000.)
        self.assertEqual(doc.data['0:hsm/sample0/h'].m_percent, True)
#		self.assertEqual(doc.data['/hsm/sample0/Width'].m_initialDimension,2000.)
#		self.assertEqual(doc.data['/hsm/sample0/Width'].m_percent,False)

    @unittest.skip('')
    def test_8a_importConvertedDil(self):
        # Dilatometer test
        op = convert.convert(iut.db3_path, '00005H', force=True)
        self.assertTrue(op)
        doc = self.check_import(op, dil_names)
        self.assertEqual(
            doc.data['0:horizontal/sample0/Dil'].m_initialDimension, 51000.)
        self.assertEqual(doc.data['0:horizontal/sample0/Dil'].m_percent, True)
        self.assertEqual(
            doc.data['0:horizontal/sample0/camA'].m_initialDimension, 51000.)
        self.assertEqual(doc.data['0:horizontal/sample0/camA'].m_percent, False)
        self.assertEqual(
            doc.data['0:horizontal/sample0/camB'].m_initialDimension, 51000.)
        self.assertEqual(doc.data['0:horizontal/sample0/camB'].m_percent, False)

    @unittest.skip('')
    def test_8b_importConvertedFlex(self):
        # Dilatometer test
        op = convert.convert(iut.db3_path, '00006F', force=True)
        self.assertTrue(op)
        doc = self.check_import(op, flex_names)
        self.assertEqual(
            doc.data['0:flex/sample0/Flex'].m_initialDimension, 70000.)
        self.assertEqual(doc.data['0:flex/sample0/Flex'].m_percent, True)
        self.assertEqual(
            doc.data['0:flex/sample0/camA'].m_initialDimension, 70000.)
        self.assertEqual(doc.data['0:flex/sample0/camA'].m_percent, False)

    @unittest.skip('')
    def test_9_toArchive(self):
        op = convert.convert(iut.db3_path, '00001S', force=True, keep_img=True)
        # problema widgetregistry
        mw = browser.MainWindow()
        mw.open_file(op)

    @unittest.skip('')
    def test_double_samples(self):
        op = convert.convert(iut.db3_path, '00008L', force=True, keep_img=True)
        self.assertTrue(op, 'Conversion Failed')
        self.check_images(op, 'm3')
        self.check_import(op, hsmDoble_names)
        op = convert.convert(iut.db3_path, '00008R', force=True, keep_img=True)
        self.assertTrue(op, 'Conversion Failed')
        self.check_images(op, 'm3')
        self.check_import(op, hsmDoble_names)

    @unittest.skip('')
    def test_softening(self):
        op = convert.convert(iut.db3_path, '00011S', force=True)
        self.check_import(op, hsm_names)
        op = convert.convert(iut.db3_path, '00010R', force=True)
        self.check_import(op, hsmDoble_names)
        op = convert.convert(iut.db3_path, '00010L', force=True)
        self.check_import(op, hsmDoble_names)

if __name__ == "__main__":
    unittest.main()
