#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing MisuraDocument (mdoc.py module)"""
import unittest
import sys
import os,shutil
from misura.client import filedata
from misura.canon import indexer
from misura.client.tests import iutils_testing
from PyQt4 import QtGui
from time import sleep
import veusz.document as document
import veusz.widgets

nativem4 = os.path.join(iutils_testing.data_dir,'test_video.h5')


class MisuraDocument(unittest.TestCase):
	def setUp(self):
		f = indexer.SharedFile(nativem4)
		self.original_elapsed_time = f.get_node_attr('/conf','elapsed')
		f.close()
		
	def tearDown(self):
		f = indexer.SharedFile(nativem4)
		f.set_node_attr('/conf','elapsed',self.original_elapsed_time)
		f.close()
		
	@unittest.skip('not testable without a real server... or ConfigurationProxy should implement time() and from_column()')
	def test_update(self):
		# Reduce elapsed time by a half
		elapsed_time = self.original_elapsed_time/2.
		f = indexer.SharedFile(nativem4)
		f.set_node_attr('/conf', 'elapsed', elapsed_time)
		doc = filedata.MisuraDocument(proxy=f)
		doc.reloadData()
		doc.root = f.conf
# 		# This will import only a half of the points
# 		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
# 		imp.do(doc)
		nt=len(doc.data['0:t'].data)
		nh=len(doc.data['0:hsm/sample0/h'].data)
		lastt=doc.data['0:t'].data[-1]

		f.set_node_attr('/conf','elapsed', self.original_elapsed_time)

		r = doc.update()
		nt1=len(doc.data['0:t'].data)
		nh1=len(doc.data['0:hsm/sample0/h'].data)
		lastt1=doc.data['0:t'].data[-1]

		self.assertEqual([nt1,nh1], [nt,nh])	
		# self.assertLess(abs(2*lastt-lastt1),doc.interval)

		# # Empty update
		r=doc.update()
		self.assertEqual(r,[])	
		f.close()
		
	def test_get_row(self):
		doc=filedata.MisuraDocument(filename=nativem4)
		doc.reloadData()
		row=doc.get_row(5)
		
	
if __name__ == "__main__":
	unittest.main()  