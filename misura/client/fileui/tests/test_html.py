#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import os

from misura.client.fileui import html

class Html(unittest.TestCase):
	def test__embed_empty_image(self):
		expected_html = "<img src='data:image/gif;base64,' alt=''>"

		self.assertEqual(expected_html, html.embed("", "gif"))

	def test_embed_image_in_base64(self):
		data = "any data"
		expected_html = "<img src='data:image/gif;base64,YW55IGRhdGE=' alt=''>"

		self.assertEqual(expected_html, html.embed("any data", "gif"))

	def test_table_no_inages(self):
		expected_html = "<table><tr></tr></table>"

		self.assertEqual(expected_html, html.table_from([]))

	def test_table_with_one_image(self):
		image_html = "<img src='data:image/gif;base64,YW55IGRhdGE=' alt=''>"
		expected_html = "<table><tr><td>%s</td></tr></table>" % image_html

		self.assertEqual(expected_html, html.table_from(['any data']))

	def test_table_with_two_images(self):
		image_html1 = "<img src='data:image/gif;base64,YW55IGRhdGEgMQ==' alt=''>"
		image_html2 = "<img src='data:image/gif;base64,YW55IGRhdGEgMg==' alt=''>"

		expected_html = "<table><tr><td>%s</td><td>%s</td></tr></table>" % (image_html1, image_html2)

		self.assertEqual(expected_html, html.table_from(['any data 1', 	'any data 2']))

	def test_table_with_six_images(self):
		image_html = "<img src='data:image/gif;base64,YW55IGRhdGE=' alt=''>"

		expected_html = "<table><tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr><tr><td>%s</td></tr></table>" % (image_html, image_html, image_html, image_html, image_html, image_html)

		self.assertEqual(expected_html, html.table_from(['any data', 'any data', 'any data', 'any data', 'any data', 'any data']))

	def test_base64_from_image_file(self):
		image_file_name = os.path.dirname(os.path.abspath(__file__)) +  "/images/ta-logo.gif"
		expected_encoded_image_start = "R0lGODlhUwBGANUAAL/K2H+WsEBiid/"

		actual_encoded_image = html.encode_image(image_file_name)

		self.assertTrue(actual_encoded_image.startswith(expected_encoded_image_start), "'%s' does not start with '%s'" % (actual_encoded_image, expected_encoded_image_start))

	def test_image_with_labels(self):
		temperature = "22"
		time = "01:14"
		image_html = "<img src='data:image/gif;base64,YW55IGRhdGE=' alt=''>"

		actual_image_html = html.embed_with_labels("any data", temperature, time)

		expected_image_html = "<table><tr><td><img src='data:image/gif;base64,YW55IGRhdGE=' alt=''></td></tr>"
		expected_image_html += "<tr><td>22&deg;</td></tr><tr><td>01:14</td></tr></table>"

		self.assertEqual(expected_image_html, actual_image_html)





if __name__ == "__main__":
    unittest.main()