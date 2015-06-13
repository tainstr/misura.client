#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing the client-side standard execution."""
import unittest
import os
from misura.canon.logger import Log as logging
from misura.client import filedata
import iutils_testing as iut
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


from3=os.path.join(iut.data_dir,'m3_hsm.h5')
nativem4=os.path.join(iut.data_dir,'post_m3.h5')

@unittest.skip('')
class TestRestandard(unittest.TestCase):
	"""Tests client-side scripts management."""	
				
		
#	@unittest.skip('')
	def test_restandard(self):
		"""Tests the distribution of scripts"""
		fp=filedata.getFileProxy(nativem4)
		fp.conf.post.distribute_scripts()
		correct=fp.conf.post.sample0['Melting']
		# Set a wrong value
		fp.conf.post.sample0['Melting']={'point': 0, 'value': 0, 'temp': 0, 'time': 0}
		# Check if it is really set
		self.assertEqual(fp.conf.post.sample0['Melting'],{'point': 0, 'value': 0, 'temp': 0, 'time': 0})
		sumTable=fp.test.uid(fp.uid).test.root.summary
		fp.conf.post.characterization(sumTable)
		# Set if the correct value is back
		self.assertEqual(fp.conf.post.sample0['Melting'],correct)
		fp.close()
		
		
		
		
		
if __name__ == "__main__":
    unittest.main()  
