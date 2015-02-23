# -*- coding: utf-8 -*-

# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class NullDao(object):
    """ Null DAO class for elements that don't need any metadata (such
    as DocumentSet). It has the minimum API required to work with
    formatCIM.py.
    """

    def __init__(self, connect_env):
        pass

    def daos_for_node(self, constraint):
        return [self]

    def metadata(self, constraint):
        pass
