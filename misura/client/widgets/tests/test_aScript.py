# -*- coding: utf-8 -*-
#!/usr/bin/python
"""Tests aScript widget."""
import unittest
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui,QtCore
app=False
print 'Importing',__name__
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	print 'Quitting app'
	app.quit()
	print 'tearDownModule',__name__
	
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
