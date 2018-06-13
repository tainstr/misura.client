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
        [('time', 'Float'), ('Temp', 'Float'), ('value', 'Float')],
        (1, 2, 3), (10, 20, 30), (100, 200, 300)])
    proxy.add_option('non_float', 'Table', [
        [('time', 'Float'), ('T', 'Float'), ('value', 'String')],
        (1, 2, 'a'), ])

    proxy.add_option('double_time', 'Table', [
        [('time', 'Float'), ('Time', 'Float'), ('value', 'Float')],
        (1, 2, 3), ])
    return proxy

class GenerateDatasetsUtilities(unittest.TestCase):
    def test_search_column_name(self):
        def check(names, func, expected):
            r = gd.search_column_name(names,
                                      func)
            self.assertEqual(r, expected)

        check(['time', 'a', 'b'], gd.is_time_col, ('time', 0))
        check(['q', 'Time', 'a', 'b'], gd.is_time_col, ('Time', 1))
        # Take first
        check(['q', 'time', 'a', 'Time'], gd.is_time_col, ('time', 1))

        check(['Temp', 'a', 'b'], gd.is_T_col, ('Temp', 0))
        check(['q', 'Temp', 'a', 'b'], gd.is_T_col, ('Temp', 1))
        # Take first
        check(['q', 'Temp.', 'a', 'temperature'],
              gd.is_T_col, ('Temp.', 1))
        
        check(['err', 'a', 'b'], gd.is_error_col, ('err', 0))
        check(['q', 'Error', 'a', 'b'], gd.is_error_col, ('Error', 1))
        check(['q', 'error', 'a', 'Error'], gd.is_error_col, ('error', 1))
        
class GenerateDatasets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        f = indexer.SharedFile(nativem4)
        cls.doc = filedata.MisuraDocument(proxy=f)
        cls.doc.reloadData()
        f.close()

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
        datasets = {'0:a/b/c': ([1, 2, 3], 'Test', 'Test dataset', False, None)}
        original_dataset = self.doc.data['0:kiln/T']
        gd.add_datasets_to_doc(datasets, self.doc, original_dataset)
        self.assertIn('0:a/b/c', self.doc.data)
        self.check_dataset(self.doc.data['0:a/b/c'], unit=False)
        
    def check_generated(self, proxy):
        self.assertIn('0:ok', self.doc.data)
        self.assertEqual(list(self.doc.data['0:ok'].data), [3, 30, 300])
        self.assertIn('0:ok_t', self.doc.data)
        self.assertEqual(list(self.doc.data['0:ok_t'].data), [1, 10, 100])
        self.assertIn('0:ok_T', self.doc.data)
        self.assertEqual(list(self.doc.data['0:ok_T'].data), [2, 20, 200])
        
    def cleanup(self):
        if not '0:ok' in self.doc.data:
            return
        del self.doc.data['0:ok']
        del self.doc.data['0:ok_t']
        del self.doc.data['0:ok_T']

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
    unittest.main(verbosity=2)
