#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests Archive"""
import unittest
import os
from misura import utils_testing as ut

from misura import server
from misura.client import conf 
from misura.client import filedata

from misura.client.tests import iutils_testing as iut
from PyQt4 import QtGui

print 'Importing',__name__
main=__name__=='__main__'


def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])
	
def tearDownModule():
	app.quit()
	print 'tearDownModule',__name__
	
# nativem4=os.path.join(iut.data_dir,'post_m3.h5')


#@unittest.skip('')
class TestTreePanel(unittest.TestCase):
#	@unittest.skip('')
	def test_recursiveModel(self):
		s=server.MainServer()
		print '######## STARTING MCONF #######'*10
		m=conf.TreePanel(s.users,select=s.users)
		if main:
			m.show()
			app.exec_()
		
		

if __name__=="__main__":
	unittest.main()  
		
		
