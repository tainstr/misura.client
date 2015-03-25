#!/usr/bin/python
# -*- coding: utf-8 -*-
"""misura Configuration Manager"""
import unittest
from misura.client import clientconf, confwidget
import tempfile
from PyQt4 import QtGui
app=False

print 'Importing',__name__

def setUpModule():
	print 'setUpModule',__name__
	global app
	app=QtGui.QApplication([])

def tearDownModule():
	global app
	app.quit()
	print 'tearDownModule',__name__
	
class Conf(unittest.TestCase):
#	@unittest.skip('')
	def test_create(self):
#		f,p=tempfile.mkstemp()
		f=tempfile.NamedTemporaryFile(delete=False)
		p=f.name
		f.close() # Compatibilità Windows: i file temporanei devono essere aperti e chiusi...!!!
		cf=clientconf.ConfDb(p,new=True)
		k0=set(clientconf.default_desc.keys())
		k1=set(cf.desc.keys())
		self.assertEqual(k0,k1)
	
#	@unittest.skip('')
	def test_save(self):
#		f,p=tempfile.mkstemp()
		f=tempfile.NamedTemporaryFile(delete=False)
		p=f.name
		f.close()
		cf=clientconf.ConfDb(p,new=True)
		cf['lang']='en'
		cf.save()
		cf=clientconf.ConfDb(p)
		self.assertEqual(cf['lang'],'en')
		
#	@unittest.skip('')	
	def test_mem(self):
#		f,p=tempfile.mkstemp()
		f=tempfile.NamedTemporaryFile(delete=False)
		p=f.name
		f.close()
		cf=clientconf.ConfDb(p,new=True)
		cf.mem('file','name1','path1')
		cf.mem_file('name2','path2')
		self.assertEqual(cf.recent_file,[['name1','path1'],['name2','path2']])
		for i in range(10):
			cf.mem_file(str(i),str(i))
		print 'RECENT FILE',cf.recent_file
		self.assertEqual(cf.recent_file[7],['5','5'])
		cf.save()
		o=cf.recent_file[:]
		cf=clientconf.ConfDb(p)
		print 'RECENT FILE AFTER SAVING',o
		print 'RECENT FILE AFTER OPENING',cf.recent_file
		
		self.assertEqual(cf.recent_file,o)
	
#	@unittest.skip('')	
	def test_unicode(self):
		f=tempfile.NamedTemporaryFile(delete=False)
		cf=clientconf.ConfDb(f.name,new=True)
		f.close()
		cf.mem_file( u'Vallourec - 126F3 80\xb0C/min 3x3','/home/daniele/tmp/gr/Vallourec - 126F3 80Cmin 3x3_00612S.h5')
		
	@unittest.skipIf(__name__!='__main__','Interactive')
	def test_widget(self):
		cc=confwidget.ClientConf()
		cc.show()
		app.exec_()
	


if __name__ == "__main__":
	unittest.main()   
