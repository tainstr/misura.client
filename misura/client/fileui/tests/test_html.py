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
		expected_html = "<table>\
<tr><td><table><tr><td>%s</td></tr><tr><td><b>56</b></td></tr><tr><td>4&deg;C</td></tr>\
<tr><td>00:10</td></tr></table></td></tr></table>" % image_html

		self.assertEqual(expected_html, html.table_from([['any data', 56, 4, '00:10']]))

	def test_table_with_six_images(self):
		image_html = "<img src='data:image/gif;base64,YW55IGRhdGE=' alt=''>"

		expected_html = "<table><tr>\
<td><table><tr><td>%s</td></tr><tr><td><b>1</b></td></tr><tr><td>10&deg;C</td></tr><tr><td>a time 1</td></tr></table></td>\
<td><table><tr><td>%s</td></tr><tr><td><b>2</b></td></tr><tr><td>20&deg;C</td></tr><tr><td>a time 2</td></tr></table></td>\
<td><table><tr><td>%s</td></tr><tr><td><b>3</b></td></tr><tr><td>30&deg;C</td></tr><tr><td>a time 3</td></tr></table></td>\
<td><table><tr><td>%s</td></tr><tr><td><b>4</b></td></tr><tr><td>40&deg;C</td></tr><tr><td>a time 4</td></tr></table></td>\
<td><table><tr><td>%s</td></tr><tr><td><b>5</b></td></tr><tr><td>50&deg;C</td></tr><tr><td>a time 5</td></tr></table></td>\
</tr>\
<tr>\
<td><table><tr><td>%s</td></tr><tr><td><b>6</b></td></tr><tr><td>60&deg;C</td></tr><tr><td>a time 6</td></tr></table></td>\
</tr></table>" % (image_html, image_html, image_html, image_html, image_html, image_html)

		data = [
			 ['any data', 1, 10, 'a time 1'],
			 ['any data', 2, 20, 'a time 2'],
			 ['any data', 3, 30, 'a time 3'],
			 ['any data', 4, 40, 'a time 4'],
			 ['any data', 5, 50, 'a time 5'],
			 ['any data', 6, 60, 'a time 6']
		]

		self.assertEqual(expected_html, html.table_from(data))

	def test_base64_from_image_file(self):
		image_file_name = os.path.dirname(os.path.abspath(__file__)) +  "/images/ta-logo.gif"
		expected_encoded_image_start = "R0lGODlhUwBGANUAAL/K2H+WsEBiid/"

		actual_encoded_image = html.encode_image(image_file_name)

		self.assertTrue(actual_encoded_image.startswith(expected_encoded_image_start), "'%s' does not start with '%s'" % (actual_encoded_image, expected_encoded_image_start))

	def test_image_with_labels(self):
		temperature = "22"
		time = "01:14"
		image_html = "<img src='data:image/gif;base64,YW55IGRhdGE=' alt=''>"

		actual_image_html = html.embed_with_labels("any data", 456, temperature, time)

		expected_image_html = "<table><tr><td><img src='data:image/gif;base64,YW55IGRhdGE=' alt=''></td></tr>"
		expected_image_html += "<tr><td><b>456</b></td></tr><tr><td>22&deg;C</td></tr><tr><td>01:14</td></tr></table>"

		self.assertEqual(expected_image_html, actual_image_html)





if __name__ == "__main__":
    unittest.main()