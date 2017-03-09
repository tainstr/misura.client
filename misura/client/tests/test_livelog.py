#!/usr/bin/python
# -*- coding: utf-8 -*-
"""misura Configuration Manager"""
import unittest
from misura.client.tests import iutils_testing
from misura.client import livelog
from misura.client.live import registry

class LiveLog(unittest.TestCase):

    def test_no_updates_when_log_is_unchanged(self):
        registry.log_buf = [1,2,3,4]
        log = livelog.LiveLog()
        log.current_buf = [1,2,3,4]

        log.slotUpdate()

        self.assertEquals([1,2,3,4], log.current_buf)

    def test_update(self):
        registry.log_buf = [1,2,3,4]
        log = livelog.LiveLog()
        log.current_buf = [1,2]

        log.slotUpdate()

        self.assertEquals([1,2], log.current_buf)


if __name__ == "__main__":
    unittest.main()
