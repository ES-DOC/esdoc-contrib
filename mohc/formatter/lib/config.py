# -*- coding: utf-8 -*-

import ConfigParser
import os

# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 see
# <http://www.gnu.org/licenses/>

class FormatConfig(object):

    def __init__(self, dir=None):
        if not dir:
            dir = os.path.dirname(__file__)
            dir = os.path.join(dir, "..", "etc")
        self.cfg_path = os.path.join(dir, "format.cfg")

    def config_path(self):
        return self.cfg_path
            
    def read_config(self):
        config = ConfigParser.RawConfigParser()
        config.read(self.cfg_path)
        cfg = {}
        for sect in config.sections():
            cfg[sect] = dict(config.items(sect))
        return cfg
