#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest

from misura.client.fileui import html

class Html(unittest.TestCase):
	def test__embed_empty_image(self):
		expected_html = "<img src='data:image/jpg;base64,' alt=''>"

		self.assertEqual(expected_html, html.embed("", "jpg"))

	def test_embed_image_in_base64(self):
		data = "any data"
		expected_html = "<img src='data:image/jpg;base64,YW55IGRhdGE=' alt=''>"

		self.assertEqual(expected_html, html.embed("any data", "jpg"))




if __name__ == "__main__":
    unittest.main()