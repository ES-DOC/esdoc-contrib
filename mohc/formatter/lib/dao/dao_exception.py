# -*- coding: utf-8 -*-

# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class DaoConnectionException(Exception):
    """ Exception raised for dao connection problems. """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class DaoMetadataException(Exception):
    """ Exception raised for metadata issues we can't resolve that
    would result in invalid CIM documents (such as a simulation with
    multiple calendars).
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class DaoContractException(Exception):
    """ Exception raised if a dao breaches the contract to supply the
    metadata required to create a valid CIM element with pyesdoc.
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
