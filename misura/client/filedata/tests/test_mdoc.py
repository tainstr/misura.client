#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing MisuraDocument (mdoc.py module)"""
import unittest
import sys
import os,shutil
from misura.client import filedata
from misura.canon import indexer
from misura.client.tests import iutils_testing as iut
from PyQt4 import QtGui
from time import sleep
import veusz.document as document
import veusz.widgets
app=False

print 'Importing',__name__
nativem4=os.path.join(iut.data_dir,'hsm_test.h5')


def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	app.quit()
	print 'tearDownModule',__name__
	
class MisuraDocument(unittest.TestCase):
	def setUp(self):
		
		f=indexer.SharedFile(nativem4)
		self.original_elapsed=f.get_node_attr('/conf','elapsed')
		f.close()
		
	def tearDown(self):
		f=indexer.SharedFile(nativem4)
		f.set_node_attr('/conf','elapsed',self.original_elapsed)
		f.close()
		
	def test_update(self):
		# Reduce elapsed time by a half
		elp=self.original_elapsed/2.
		print 'elapsed',self.original_elapsed,elp
		f=indexer.SharedFile(nativem4)
		f.set_node_attr('/conf','elapsed',elp)
		doc=filedata.MisuraDocument(proxy=f)
		doc.reloadData()
# 		# This will import only a half of the points
# 		imp=filedata.OperationMisuraImport(filedata.ImportParamsMisura(filename=nativem4))
# 		imp.do(doc)
		nt=len(doc.data['0:t'].data)
		nh=len(doc.data['hsm.sample0.h'].data)
		lastt=doc.data['0:t'].data[-1]
		print 'first import',doc.data['0:t'].data
		# Restore the original elapsed value
		f.set_node_attr('/conf','elapsed',self.original_elapsed)
		# Try to update
		r=doc.update()
		print 'updated',r
		print 'second import',doc.data['0:t'].data
		nt1=len(doc.data['0:t'].data)
		nh1=len(doc.data['hsm.sample0.h'].data)
		lastt1=doc.data['0:t'].data[-1]
		self.assertEqual([nt1,nh1],[2*nt,2*nh])	
		self.assertLess(abs(2*lastt-lastt1),doc.interval)
		# Empty update
		r=doc.update()
		self.assertEqual(r,[])	
		f.close()
		
	def test_get_row(self):
		doc=filedata.MisuraDocument(filename=nativem4)
		doc.reloadData()
		row=doc.get_row(5)
		print row
		
	
if __name__ == "__main__":
	unittest.main()  