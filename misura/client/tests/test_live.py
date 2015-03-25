#!/usr/bin/python
# -*- coding: utf-8 -*-
print 'Importing '+__name__

import unittest
from time import sleep
from misura import utils_testing as ut
from misura.client.tests import iutils_testing as iut
from misura import server

from misura.client.live import registry
from misura.client import widgets

class KidRegistry(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.root=server.BaseServer()
		registry.obj=cls.root
		iut.enableSignalDebugging()
		
	def setUp(self):
		registry.clear()
	
	def test_clear(self):
		w=widgets.Active(self.root, self.root, self.root.gete('name'))
		registry.clear()
		self.assertEqual(len(registry.rid), 0)
		self.assertEqual(len(registry.times), 0)
	
	def test_register(self):
		# Registering
		w=widgets.Active(self.root, self.root, self.root.gete('name'))
		kid=w.kid
		# The widget should be already registered
		self.assertEqual(registry.times.get(kid, None), 0)
		self.assertEqual(registry.rid.get(kid, None), [w])
		# Trying registering again the same widget should not change anything
		kid=registry.register(w)
		self.assertEqual(kid, w.kid)
		self.assertEqual(registry.times.get(kid, None), 0)
		self.assertEqual(registry.rid.get(kid, None), [w])
			
		# Register one more, with the same kid (but it's a different object!)
		w1=widgets.Active(self.root,self.root,self.root.gete('name'))
		kid=w1.kid
		self.assertEqual(registry.times.get(kid, None), 0)
		self.assertEqual(registry.rid.get(kid, None), [w,w1])
		# Unregistering w1
		registry.unregister(w1)
		self.assertEqual(registry.rid.get(kid, None), [w])	
		self.assertEqual(registry.times.get(kid, None), 0)
		# Unregistering w
		registry.unregister(w)
		self.assertEqual(registry.rid.get(kid, None), None)	
		self.assertEqual(registry.times.get(kid, None), None)	
	
	def test_update_all(self):
		up=registry.update_all()
		# Using ActiveObjcect cause we need signals
		w=widgets.ActiveObject(self.root, self.root, self.root.gete('name'))
		w1=widgets.ActiveObject(self.root, self.root, self.root.gete('comment'))
		up=registry.update_all()
		self.assertSetEqual(set(up), set([w, w1]))
		up=registry.update_all()
		self.assertEqual(up, [])
		self.root['name']='ciccio'
		up=registry.update_all()
		self.assertEqual(up, [w])
		self.assertEqual(w.current, 'ciccio')
		self.root['comment']='pippo'
		up=registry.update_all()
		self.assertEqual(up, [w1])
		self.assertEqual(w1.current, 'pippo')
		up=registry.update_all()
		self.assertEqual(up, [])
		
	

if __name__ == "__main__":
	unittest.main(verbosity=2)
