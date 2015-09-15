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

	def test_table_no_inages(self):
		expected_html = "<table><tr></tr></table>"

		self.assertEqual(expected_html, html.table_from([]))

	def test_table_with_one_image(self):
		image_html = "<img src='data:image/jpg;base64,YW55IGRhdGE=' alt=''>"
		expected_html = "<table><tr><td>%s</td></tr></table>" % image_html

		self.assertEqual(expected_html, html.table_from(['any data']))

	def test_table_with_two_images(self):
		image_html1 = "<img src='data:image/jpg;base64,YW55IGRhdGEgMQ==' alt=''>"
		image_html2 = "<img src='data:image/jpg;base64,YW55IGRhdGEgMg==' alt=''>"

		expected_html = "<table><tr><td>%s</td><td>%s</td></tr></table>" % (image_html1, image_html2)

		self.assertEqual(expected_html, html.table_from(['any data 1', 	'any data 2']))

	def test_table_with_six_images(self):
		image_html = "<img src='data:image/jpg;base64,YW55IGRhdGE=' alt=''>"

		expected_html = "<table><tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr><tr><td>%s</td></tr></table>" % (image_html, image_html, image_html, image_html, image_html, image_html)

		self.assertEqual(expected_html, html.table_from(['any data', 'any data', 'any data', 'any data', 'any data', 'any data']))




if __name__ == "__main__":
    unittest.main()