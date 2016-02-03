#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from misura.client.plugin import utils


class UtilsTests(unittest.TestCase):
    def test_clean_separators(self):
        separators = ['/', '-', '_', ' ']
        string_with_separators = "a string/with-a-lot/of_separators-of_any/kind"
        expected_string = "astringwithalotofseparatorsofanykind"

        self.assertEqual(expected_string,
                         utils.clean_separators(string_with_separators,
                                                 separators))


if __name__ == "__main__":
    unittest.main()
