#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
logging.debug('%s', 'Importing '+__name__)

import unittest
from misura.canon.logger import Log as logging
from time import sleep
from misura import utils_testing
from misura.client.tests import iutils_testing
from misura import server

from misura.client.live import registry
from misura.client import widgets
from misura.canon import option

class KidRegistry(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.root=option.ConfigurationProxy(server.BaseServer().tree()[0])
		registry.obj=cls.root
		iutils_testing.enableSignalDebugging()
		
	def setUp(self):
		registry.clear()
	
	def test_clear(self):
		w=widgets.Active(self.root, self.root, self.root.gete('name'))
		registry.register(w)
		
		self.assertEqual(len(registry.rid), 1)
		self.assertEqual(len(registry.times), 1)


		registry.clear()

		self.assertEqual(len(registry.rid), 0)
		self.assertEqual(len(registry.times), 0)
	
	def test_register(self):
		widget = widgets.Active(self.root, self.root, self.root.gete('name'))
		registry.register(widget)
		key_id = widget.prop['kid']

		self.assertEqual(registry.times.get(key_id, "Value not found"), 0)
		self.assertEqual(registry.rid.get(key_id, "Value not found"), [widget])

	def test_register_twice_the_same_widget(self):
		widget = widgets.Active(self.root, self.root, self.root.gete('name'))
		registry.register(widget)
		key_id = widget.prop['kid']

		self.assertEqual(registry.times.get(key_id, "Value not found"), 0)
		self.assertEqual(registry.rid.get(key_id, "Value not found"), [widget])

		key_id = registry.register(widget)
		self.assertEqual(key_id, widget.prop['kid'])
		self.assertEqual(registry.times.get(key_id, "Value not found"), 0)
		self.assertEqual(registry.rid.get(key_id, "Value not found"), [widget])
			
	def test_register_different_widgets(self):
		widget = widgets.Active(self.root, self.root, self.root.gete('name'))
		registry.register(widget)
		key_id = widget.prop['kid']

		self.assertEqual(registry.times.get(key_id, "Value not found"), 0)
		self.assertEqual(registry.rid.get(key_id, "Value not found"), [widget])


		another_widget = widgets.Active(self.root, self.root, self.root.gete('name'))
		registry.register(another_widget)
		
		self.assertEqual(registry.times.get(key_id, "Value not found"), 0)
		self.assertEqual(registry.rid.get(key_id, "Value not found"), [widget, another_widget])
		
		registry.unregister(another_widget)
		self.assertEqual(registry.rid.get(key_id, "Value not found"), [widget])
		self.assertEqual(registry.times.get(key_id, "Value not found"), 0)
		
		registry.unregister(widget)
		self.assertEqual(registry.rid.get(key_id, "Value not found"), "Value not found")	
		self.assertEqual(registry.times.get(key_id, "Value not found"), "Value not found")	

	@unittest.skip('')	
	def test_update_all(self):
		up = registry.update_all()
		# Using ActiveObjcect cause we need signals
		widget = widgets.ActiveObject(self.root, self.root, self.root.gete('name'))
		another_widget = widgets.ActiveObject(self.root, self.root, self.root.gete('comment'))

		up = registry.update_all()
		self.assertSetEqual(set(up), set([widget, another_widget]))

		up = registry.update_all()
		self.assertEqual(up, [])
		self.root['name']='ciccio'

		up=registry.update_all()
		self.assertEqual(up, [widget])
		self.assertEqual(widget.current, 'ciccio')
		self.root['comment']='pippo'

		up=registry.update_all()
		self.assertEqual(up, [another_widget])
		self.assertEqual(another_widget.current, 'pippo')
		
		up=registry.update_all()
		self.assertEqual(up, [])
		
	

if __name__ == "__main__":
	unittest.main(verbosity=2)
