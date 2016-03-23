#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest

from misura.client.fileui import template

class Template(unittest.TestCase):
	def test_empty(self):
		self.assertEqual("", template.convert("", {}))

	def test_one_substitution(self):
		template_text = "any text $TO_CHANGE$ any other text"

		expected_output = "any text changed with any other text"

		self.assertEqual(expected_output, template.convert(template_text, {"$TO_CHANGE$": "changed with"}))

	def test_two_substitution(self):
		template_text = "any text $TO_CHANGE1$ any other {{{TO_CHANGE2}}} text"

		expected_output = "any text should be changed with any other changed text"

		substitutions_hash = {"$TO_CHANGE1$": "should be changed with",
				     "{{{TO_CHANGE2}}}": "changed"}

		self.assertEqual(expected_output, template.convert(template_text, substitutions_hash))


if __name__ == "__main__":
    unittest.main()
