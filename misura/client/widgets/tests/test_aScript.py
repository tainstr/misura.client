# -*- coding: utf-8 -*-
#!/usr/bin/python
"""Tests aScript widget."""
import unittest
from misura.canon.logger import Log as logging
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui,QtCore
app=False
logging.debug('%s %s', 'Importing', __name__)
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	logging.debug('%s', 'Quitting app')
	app.quit()
	logging.debug('%s %s', 'tearDownModule', __name__)
	
class aScript(unittest.TestCase):
	def setUp(self):
		self.root=option.ConfigurationProxy()
		
	def wgGen(self):
		self.assertTrue(self.root.has_key('test'))
		w=widgets.build(self.root, self.root, self.root.gete('test'))
		# The current value is not initialized (gete() returns {current:None} )
		self.assertTrue(w is not False)
		return w
		
	def test_String(self):
		self.root.sete('test', option.ao({}, 'test', 'Script')['test'])
		w=self.wgGen()
		if __name__=='__main__':
			w.show()
			QtGui.qApp.exec_()
			
	
			
if __name__ == "__main__":
	unittest.main(verbosity=2)  
