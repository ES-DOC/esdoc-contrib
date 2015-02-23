# -*- coding: utf-8 -*-

import unittest
import sys

import formatCIM


class TestFormatCIMUsage(unittest.TestCase):

    def setUp(self):
        sys.argv = ["formatCIM.py"]

    def test_invalid_option(self):
        sys.argv = sys.argv + ["-Q"]
        self.assertRaises(SystemExit, formatCIM.check_usage)

    def test_with_valid_set_of_options(self):
        valid = [
            "-f", "xml", "-d", "model", "-m", "HadGEM2-ES",
            "-o", "foo", "-p", "CMIP5", "-t", "foo"]
        sys.argv = sys.argv + valid
        formatCIM.check_usage()
        self.assertTrue(True)

    def test_project_mandatory(self):
        invalid = [
            "-f", "xml", "-d", "model", "-m", "HadGEM2-ES",
            "-o", "foo", "-t", "foo"]
        sys.argv = sys.argv + invalid
        self.assertRaises(SystemExit, formatCIM.check_usage)

    def test_template_mandatory(self):
        invalid = [
            "-f", "xml", "-d", "model", "-m", "HadGEM2-ES",
            "-o", "foo", "-p", "cmip5"]
        sys.argv = sys.argv + invalid
        self.assertRaises(SystemExit, formatCIM.check_usage)

    def test_missing_model_info(self):
        sys.argv = sys.argv + [
            "-f", "xml", "-d", "model", "-o", "foo", "-p", "CMIP5",
            "-t", "foo"]
        self.assertRaises(SystemExit, formatCIM.check_usage)

    def test_missing_submodel_info(self):
        sys.argv = sys.argv + [
            "-f", "xml", "-d", "submodel", "-s", "Atmosphere",
            "-o", "foo", "-p", "CMIP5", "-t", "foo"]
        self.assertRaises(SystemExit, formatCIM.check_usage)

    def test_missing_expt_info(self):
        sys.argv = sys.argv + [
            "-f", "xml", "-d", "experiment", "-o", "foo", "-p",
            "CMIP5", "-t", "foo"]
        self.assertRaises(SystemExit, formatCIM.check_usage)

    def test_expt_needs_model(self):
        sys.argv = sys.argv + [
            "-f", "xml", "-d", "experiment", "-e", "rcp85",
            "-o", "foo", "-p", "CMIP5", "-t", "foo"]
        self.assertRaises(SystemExit, formatCIM.check_usage)


if __name__ == "__main__":
    unittest.main()
