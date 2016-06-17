#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing MisuraDocument (mdoc.py module)"""
import unittest
import os

# must import those
import veusz.document as document
import veusz.widgets

from misura.client.tests import iutils_testing
from misura.client.filedata import generate_datasets as gd
from misura.client import filedata
from misura.canon import indexer, option

nativem4 = os.path.join(iutils_testing.data_dir, 'test_video.h5')


def make_conf_proxy():
    proxy = option.ConfigurationProxy()
    proxy.add_option('ok', 'Table', [
        [('time', 'Float'), ('T', 'Float'), ('value', 'Float')],
        (1, 2, 3), (10, 20, 30), (100, 200, 300)])
    proxy.add_option('non_float', 'Table', [
        [('time', 'Float'), ('T', 'Float'), ('value', 'String')],
        (1, 2, 'a'), ])

    proxy.add_option('double_time', 'Table', [
        [('time', 'Float'), ('t', 'Float'), ('value', 'Float')],
        (1, 2, 3), ])
    return proxy


class GenerateDatasets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        f = indexer.SharedFile(nativem4)
        cls.doc = filedata.MisuraDocument(proxy=f)
        cls.doc.reloadData()
        f.close()

    def test_search_column_name(self):
        def check(names, possible, expected):
            r = gd.search_column_name(names,
                                      possible)
            self.assertEqual(r, expected)

        check(['t', 'a', 'b'], gd.possible_timecol_names, ('t', 0))
        check(['q', 'time', 'a', 'b'], gd.possible_timecol_names, ('time', 1))
        check(['q', 't', 'a', 'Time'], gd.possible_timecol_names, (False, -1))

        check(['T', 'a', 'b'], gd.possible_Tcol_names, ('T', 0))
        check(['q', 'Temp', 'a', 'b'], gd.possible_Tcol_names, ('Temp', 1))
        check(['q', 'Temp.', 'a', 'temperature'],
              gd.possible_Tcol_names, (False, -1))

    def check_dataset(self, ds, unit='volt'):
        self.assertEqual(list(ds.data), [1, 2, 3])
        self.assertEqual(ds.m_var, 'Test')
        self.assertEqual(ds.m_label, 'Test dataset')
        print 'unit', ds.unit
        self.assertEqual(ds.unit, unit)

    def test_new_dataset_operation(self):
        original_dataset = self.doc.data['0:kiln/T']
        op = gd.new_dataset_operation(original_dataset, [1, 2, 3],
                                      'Test', 'Test dataset', '0:a/b/c', unit='volt')
        self.assertEqual(op.datasetname, '0:a/b/c')
        ds = op.dataset
        self.check_dataset(ds)

    def test_add_dataset_to_doc(self):
        datasets = {'0:a/b/c': ([1, 2, 3], 'Test', 'Test dataset')}
        original_dataset = self.doc.data['0:kiln/T']
        gd.add_datasets_to_doc(datasets, self.doc, original_dataset)
        self.assertIn('0:a/b/c', self.doc.data)
        self.check_dataset(self.doc.data['0:a/b/c'], unit=False)
        
    def check_generated(self, proxy):
        self.assertIn('0:ok', self.doc.data)
        self.assertEqual(list(self.doc.data['0:ok'].data), [3, 30, 300])
        self.assertIn('0:ok/t', self.doc.data)
        self.assertEqual(list(self.doc.data['0:ok/t'].data), [1, 10, 100])
        self.assertIn('0:ok/T', self.doc.data)
        self.assertEqual(list(self.doc.data['0:ok/T'].data), [2, 20, 200])
        
    def cleanup(self):
        if not '0:ok' in self.doc.data:
            return
        del self.doc.data['0:ok']
        del self.doc.data['0:ok/t']
        del self.doc.data['0:ok/T']

    def test_table_to_datasets(self):
        self.cleanup()
        proxy = make_conf_proxy()
        gd.table_to_datasets(proxy, proxy.gete('non_float'), self.doc)
        self.assertNotIn('0:ok', self.doc.data)
        gd.table_to_datasets(proxy, proxy.gete('double_time'), self.doc)
        self.assertNotIn('0:ok', self.doc.data)
        gd.table_to_datasets(proxy, proxy.gete('ok'), self.doc)
        self.check_generated(proxy)
        
    def test_generate_datasets(self):
        self.cleanup()
        proxy = make_conf_proxy()
        gd.generate_datasets(proxy, self.doc)
        self.check_generated(proxy)
        self.cleanup()
        gd.generate_datasets(proxy, self.doc, '^ok$')
        self.check_generated(proxy)
        self.cleanup()        
        gd.generate_datasets(proxy, self.doc, '_float$')
        self.assertNotIn('0:ok', self.doc.data)    
        
        


if __name__ == "__main__":
    unittest.main()
