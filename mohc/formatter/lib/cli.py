# -*- coding: utf-8 -*-

import getopt
import os.path
import sys

import pyesdoc

# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 see
# <http://www.gnu.org/licenses/>

class PyesdocCli(object):
    """ Utility class for command-line interface programs. """

    def __init__(self, getopt_spec, required, usage):
        self.getopt = getopt_spec
        self.required = required
        self.usage_msg = usage
        self.format = {
            "xml": pyesdoc.ESDOC_ENCODING_XML,
            "json": pyesdoc.ESDOC_ENCODING_JSON,
            "html": pyesdoc.ESDOC_ENCODING_HTML}

    def check_usage(self, argv):
        self.script_name = os.path.basename(argv[0])
        try:
            opt_pair, arg = getopt.getopt(argv[1:], self.getopt)
        except getopt.GetoptError as err:
            self.usage_exit()
        option = dict(opt_pair)
        self._check_all_required_options_defined(option)
        return option

    def usage_exit(self):
        error_msg = "USAGE: %s %s" % (self.script_name, self.usage_msg)
        self.error_exit(error_msg)

    def error_exit(self, msg):
        sys.stderr.write("%s\n" % msg)
        sys.exit(1)

    def is_format_valid(self, format):
        return format in self.format

    def encoding(self, format):
        return self.format[format]

    def _check_all_required_options_defined(self, option):
        for required in self.required:
            if required not in option:
                self.usage_exit()
        return
