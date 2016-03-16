#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import os
import base64

from misura.client.fileui import htmlreport
from misura.canon import csutil


class FakeDecoder():
    def __init__(self):
        self.__len__ = lambda: 1

    def get_data(self, i):
        return 1, ""


class HtmlReport(unittest.TestCase):
    def test_integration(self):
        csutil.find_nearest_val = lambda data, time: 123
        htmlreport.byte_array_from = lambda qimag: '789'
        base64_789_string = base64.b64encode('789')
        htmlreport.base64_logo = lambda: "a base 64 logo"
        htmlreport.images_template_text = lambda : "$LOGO$\n\
$code$\n\
$title$\n\
$date$\n\
$IMAGES_TABLE$"

        actual_report = htmlreport.create_images_report(FakeDecoder(),
                                                        {
                                                            'uid': 'an id',
                                                            'name': 'a name',
                                                            'date': 'a date'
                                                        },
                                                        "any time data",
                                                        {123: 798},
                                                        None )


        expected_images_html_table = "<table><tr><td><table>\
<tr><td>\
<img src='data:image/png;base64,%s' alt=''>\
</td></tr>\
<tr><td class='number'>1</td></tr>\
<tr><td><div class='temperature'>798&deg;C\
</div><div class='time'>0:00:01</div>\
</td></tr></table></td></tr></table>" % base64_789_string
        expected_report = "%s\n%s\n%s\n%s\n%s" % ("a base 64 logo",
            "an id",
            "a name",
            "a date",
            expected_images_html_table)

        self.assertEqual(expected_report, actual_report)


if __name__ == "__main__":
    unittest.main()
