# -*- coding: utf-8 -*-

import copy

from dao_exception import DaoConnectionException, DaoMetadataException


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class DocIdDao(object):
    """ Data access object for document ids.

    This class stores the ids of document components as a document is
    being constructed so that internal references can be used.
    """

    def __init__(self):
        self.id = {}
        self.type = ""
        self.name = ""

    def metadata(self, constraint):
        """ Finds the identifier for the specified element. """
        if self.type and self.name:
            return self._find_id(self.type, self.name)
        else:
            return self._find_id(constraint["type"], constraint["name"])

    def add_id(self, type, name, id):
        """ Adds identifier to our in-memory store. """
        self.id[self._key(type, name)] = id
        return

    def daos_for_node(self, constraint):
        """ Given a type and a container dao, find all the matching id
        entries. We may find ourself called with a name, in which case
        we short-cut and bail out.
        """
        if "name" not in constraint:
            raise DaoMetadataException('Link needs a name (which can be "")')
        if constraint["name"]:
            # We can return a single dao without having to run queries.
            self.type = constraint["type"]
            self.name = constraint["name"]
            return [self]
        if "type" not in constraint or "container_dao" not in constraint:
            raise DaoMetadataException("Link needs a type and a container")
        names = constraint["container_dao"].name_for_reference(
            {"type": constraint["type"]})
        daos = []
        for name in names:
            dao = copy.copy(self)
            dao.type = constraint["type"]
            dao.name = name
            daos.append(dao)
        return daos

    def _key(self, type, name):
        return "%s:%s" % (type, name)

    def _find_id(self, type, name):
        """ Find an id. """
        if type == "" or name == "":
            raise DaoMetadataException("Need type and name to find id")
        id_name = "%s:%s" % (type, name)
        if id_name in self.id:
            return self._make_record(self.id[id_name], type, name)
        raise DaoMetadataException("No id %s found in store" % id_name)

    def _make_record(self, id, type, name):
        return {"id": id, "type": type, "name": name}


class Null(object):
    """ Null class for documents that don't want or need to store
    their ids.
    """

    def add_id(self, type, name, id):
        pass

    def metadata(self, constraint):
        return {"null": True}
