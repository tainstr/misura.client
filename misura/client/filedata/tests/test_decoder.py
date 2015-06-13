#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests DataDecoder"""
import unittest

from misura.canon.logger import Log as logging
import os
from misura.client.tests import iutils_testing as iut
from misura.client import archive, filedata, conf

nativem4=os.path.join(iut.data_dir,'hsm_test.h5')
from PyQt4 import QtGui
app=False

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	app.quit()
	logging.debug('%s %s', 'tearDownModule', __name__)
	
#@unittest.skip('')
class DataDecoder(unittest.TestCase):
	"""Tests the MainWindow"""	
#	@unittest.skip('')
	def test(self):
		fp=filedata.getFileProxy(nativem4)
		dec=filedata.DataDecoder()
		dec.reset(fp,'/hsm/sample0/frame')
		self.assertEqual(dec.ext, 'Image')
		r=dec.get_data(0)
		self.assertTrue(os.path.exists('%s/0.dat' % dec.tmpdir))
		dec.reset(fp,'/hsm/sample0/profile')
		self.assertEqual(dec.ext, 'Profile')
		r=dec.get_data(0)
		r[1].save('datadec0.jpg' ,'JPG')
		r=dec.get_data(1)
		r[1].save('datadec1.jpg','JPG')
		r=dec.get_data(2)
		r[1].save('datadec2.jpg','JPG')	
		fp.close()	

if __name__ == "__main__":
	unittest.main(verbosity=2) 