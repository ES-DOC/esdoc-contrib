# -*- coding: utf-8 -*-

import sys
import unittest

import pyesdoc

from cli import PyesdocCli


class TestCli(unittest.TestCase):

    def setUp(self):
        self.cli = PyesdocCli(
            "c:d:f:", ["-d"], "-c dir -d doc1|doc2 [-f fmt]")

    def test_check_usage(self):
        sys.argv = ["formatCIM", "-d", "doc1"]
        try:
            option = self.cli.check_usage(sys.argv)
            self.assertEqual(len(option), 1)
            self.assertIn("-d", option)
            self.assertEqual(option["-d"], "doc1")
        except SystemExit:
            self.fail("Unexpected exit from usage check")

    def test_check_usage_with_bad_arg(self):
        sys.argv = ["formatCIM", "-x", "doc1"]
        self.assertRaises(SystemExit, self.cli.check_usage, sys.argv)

    def test_check_usage_with_missing_required_opt(self):
        sys.argv = ["formatCIM", "-c", "foo"]
        self.assertRaises(SystemExit, self.cli.check_usage, sys.argv)

    def test_is_format_valid(self):
        for valid in ["html", "json", "xml"]:
            self.assertTrue(self.cli.is_format_valid(valid))
        self.assertFalse(self.cli.is_format_valid("pdf"))

    def test_encoding(self):
        self.assertEqual(
            self.cli.encoding("xml"), pyesdoc.ENCODING_XML)


if __name__ == "__main__":
    unittest.main()
