#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import os

from misura.client.fileui import htmlreport
from misura.canon import csutil

current_dir = os.path.dirname(os.path.abspath(__file__))

class FakeDecoder():
	def __init__(self):
		self.__len__ = lambda : 1

	def get_data(self, i):
		return 1, ""

class HtmlReport(unittest.TestCase):
	def test_integration(self):
		csutil.find_nearest_val = lambda data, time: 123
		htmlreport.byte_array_from = lambda qimag: '789'

		actual_report = htmlreport.create(FakeDecoder(),
			{'uid': 'an id', 'name': 'a name', 'date': 'a date'},
			"any time data",
			{123: 798},
			current_dir + "/files/report.html",
			current_dir + "/images/fake-logo"
		)

		fake_logo_base64 = "ZmFrZSBsb2dv"
		expected_images_html_table = "<table><tr><td><table>\
<tr><td>\
<img src='data:image/png;base64,Nzg5' alt=''>\
</td></tr>\
<tr><td class='number'>1</td></tr>\
<tr><td><div class='temperature'>798&deg;C\
</div><div class='time'>0:00:01</div>\
</td></tr></table></td></tr></table>"

		expected_report = "%s\n%s\n%s\n%s\n%s" % (fake_logo_base64,
		                                      "an id",
		                                      "a name",
		                                      "a date",
		                                      expected_images_html_table)


		self.assertEqual(expected_report, actual_report)







if __name__ == "__main__":
    unittest.main()