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
<tr><td><table><tr><td align='center'><b>&nbsp;</b></td></tr><tr><td>%s</td></tr><tr>\
<td class='number'>56</td></tr><tr>\
<td><div class='temperature'>4&deg;C</div><div class='time'>00:10</div></td></tr>\
</table></td></tr></table>" % image_html

		self.assertEqual(expected_html, html.table_from([['any data', 56, 4, '00:10']]))

	def test_table_with_six_images(self):
		image_html = "<img src='data:image/gif;base64,YW55IGRhdGE=' alt=''>"

		expected_html = "<table><tr>\
<td><table><tr><td align='center'><b>&nbsp;</b></td></tr><tr><td>%s</td></tr>\
<tr><td class='number'>1</td></tr><tr><td><div class='temperature'>10&deg;C</div><div class='time'>a time 1</div></td></tr></table></td>\
<td><table><tr><td align='center'><b>&nbsp;</b></td></tr><tr><td>%s</td></tr>\
<tr><td class='number'>2</td></tr><tr><td><div class='temperature'>20&deg;C</div><div class='time'>a time 2</div></td></tr></table></td>\
<td><table><tr><td align='center'><b>&nbsp;</b></td></tr><tr><td>%s</td></tr>\
<tr><td class='number'>3</td></tr><tr><td><div class='temperature'>30&deg;C</div><div class='time'>a time 3</div></td></tr></table></td>\
<td><table><tr><td align='center'><b>&nbsp;</b></td></tr><tr><td>%s</td></tr>\
<tr><td class='number'>4</td></tr><tr><td><div class='temperature'>40&deg;C</div><div class='time'>a time 4</div></td></tr></table></td>\
<td><table><tr><td align='center'><b>&nbsp;</b></td></tr><tr><td>%s</td></tr>\
<tr><td class='number'>5</td></tr><tr><td><div class='temperature'>50&deg;C</div><div class='time'>a time 5</div></td></tr></table></td>\
</tr>\
<tr>\
<td><table><tr><td align='center'><b>&nbsp;</b></td></tr><tr><td>%s</td></tr>\
<tr><td class='number'>6</td></tr><tr><td><div class='temperature'>60&deg;C</div><div class='time'>a time 6</div></td></tr></table></td>\
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

		expected_image_html = "<table>\
<tr><td align='center'><b></b></td></tr>\
<tr><td><img src='data:image/gif;base64,YW55IGRhdGE=' alt=''></td></tr>\
<tr><td class='number'>456</td></tr><tr>\
<td><div class='temperature'>22&deg;C</div><div class='time'>01:14</div></td>\
</tr></table>"

		self.assertEqual(expected_image_html, actual_image_html)





if __name__ == "__main__":
    unittest.main()
