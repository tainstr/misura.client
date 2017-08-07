#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import os
import base64

from misura.client.fileui import htmlreport
from misura.canon import csutil

class FakeProxy():
    def rises(self, *a, **k):
        return 100, 500, 220
    
    def col_at_time(self, *a, **k):
        return 500.5, 220.1
    
    def nearest(self, p, T):
        return 100, 500, 220

class FakeDecoder():
    def __init__(self):
        self.__len__ = lambda: 1
        self.datapath = '/T'
        self.proxy = FakeProxy()

    def get_data(self, i):
        return 1, ""
    
    def get_time(self, t):
        return 501


class HtmlReport(unittest.TestCase):
    def setUp(self):
        self.old_find_nearest_val = csutil.find_nearest_val
        
    def tearDown(self):
        csutil.find_nearest_val = self.old_find_nearest_val
        
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
                                                        { # measure
                                                            'uid': 'an id',
                                                            'name': 'a name',
                                                            'date': 'a date'
                                                        },
                                                        {'Sintering':
                                                         {'temp': 'None'},
                                                         'Softening':
                                                         {'temp': 'None'},
                                                         'Sphere':
                                                         {'temp': 'None'},
                                                         'Halfsphere':
                                                         {'temp': 'None'},
                                                         'Melting':
                                                         {'temp': 'None'}
                                                        })


        expected_images_html_table = "<table><tr><td>\
<table><tr><td align='center'><b><br/><br/></b></td></tr><tr><td><img src='data:image/png;base64,Nzg5' alt=''></td></tr>\
<tr><td class='number'>1</td></tr><tr><td><div class='temperature'>220.1&deg;C</div><div class='time'>0:00:01</div></td></tr></table></td>\
<td><table><tr><td align='center'><b><br/><br/></b></td></tr><tr><td><img src='data:image/png;base64,Nzg5' alt=''></td></tr><tr><td class='number'>2</td></tr>\
<tr><td><div class='temperature'>220.1&deg;C</div><div class='time'>0:00:01</div></td></tr></table></td></tr></table>"
        expected_report = "%s\n%s\n%s\n%s\n%s" % ("a base 64 logo",
            "an id",
            "a name",
            "a date",
            expected_images_html_table)
        self.assertEqual(expected_report, actual_report)


if __name__ == "__main__":
    unittest.main()
