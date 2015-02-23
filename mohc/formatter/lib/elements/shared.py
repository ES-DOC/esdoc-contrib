# -*- coding: utf-8 -*-

import re

import pyesdoc.ontologies.cim.v1 as cim

from element import Element
from dao.dao_exception import DaoContractException


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class Citation(Element):

    def __init__(self, dao, id_dao, attribute):
        super(Citation, self).__init__(dao, id_dao, attribute)

    def container_metadata(self, parent_node):
        self.dao.container_metadata(parent_node.dao)
        return

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.Citation)
        required = ["title", "date"]
        optional = ["location", "collective_title"]
        self.populate_attr(element, metadata, required, optional)
        return element

    def add_to_doc(self, doc, model_element):
        doc.citations.append(model_element)
        return


class DocReference(Element):

    """ Class for handling references to other document elements. This
    class handles references using ids.
    """

    def __init__(self, dao, id_dao, attribute):
        super(DocReference, self).__init__(dao, id_dao, attribute)
        self.link_to = attribute["link_to"]
        self.constraint = attribute["link"]
        self.null = False

    def daos_for_node(self, constraint):
        # Override default method because we need access to two daos
        # to handle references: the dao that finds ids for elements,
        # and the container which can tell us the names of elements to
        # find ids for.
        my_constraint = dict(self.constraint)
        my_constraint["container_dao"] = self.container_dao
        return self.dao.daos_for_node(my_constraint)

    def container_metadata(self, parent_node):
        self.container_dao = parent_node.dao
        return

    def metadata(self, constraint):
        # We need to override the default because our constraints
        # are internal.
        return self.dao.metadata(self.constraint)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.DocReference)
        for required in ["id"]:
            try:
                setattr(element, required, metadata[required])
            except KeyError:
                raise DaoContractException(
                    "Missing required attr %s" % required)
        return element

    def add_to_doc(self, doc, model_element):
        # Avoid adding null references to a document.
        if self.null:
            return
        if re.match(".*references", self.link_to):
            # We are adding to a list.
            current = getattr(doc, self.link_to)
            current.append(model_element)
            setattr(doc, self.link_to, current)
        else:
            setattr(doc, self.link_to, model_element)
        return


class ReferenceByName(Element):

    """ Handles references by name. """

    def __init__(self, dao, id_dao, attribute):
        super(ReferenceByName, self).__init__(dao, id_dao, attribute)
        self.link_to = attribute["link_to"]

    def container_metadata(self, parent_node):
        self.dao.container_metadata(parent_node.dao)
        return

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.DocReference)
        required = []
        optional = ["name", "description", "type", "version"]
        possible = set(optional)
        supplied = set(metadata.keys())
        if len(possible.intersection(supplied)) == 0:
            raise DaoContractException(
                "Need at least one of the optional attributes")
        self.populate_attr(element, metadata, required, optional)
        return element

    def add_to_doc(self, doc, model_element):
        if re.match(".*references", self.link_to):
            # Adding to a list.
            current = getattr(doc, self.link_to)
            current.append(model_element)
            setattr(doc, self.link_to, current)
        else:
            setattr(doc, self.link_to, model_element)
        return


class Platform(Element):

    def __init__(self, dao, id_dao, attribute):
        super(Platform, self).__init__(dao, id_dao, attribute)

    def daos_for_node(self, constraint):
        return [self.dao]

    def cim_element(self, metadata, leaves):
        machine = self._machine(metadata)
        compiler = self._compiler(metadata)
        mcu = self.create_element(cim.MachineCompilerUnit)
        mcu.machine = machine
        mcu.compilers.append(compiler)

        element = self.create_element(cim.Platform)
        required = ["short_name"]
        optional = ["long_name"]
        self.populate_attr(element, metadata, required, optional)
        element.units.append(mcu)

        self.id_name = element.short_name
        self.id_dao.add_id("Platform", self.id_name, element.meta.id)

        return element

    def add_to_doc(self, doc, model_element):
        doc.platform = model_element
        return

    def _machine(self, metadata):
        machine = self.create_element(cim.Machine)
        try:
            setattr(machine, "name", metadata["machine_name"])
        except KeyError:
            raise DaoContractException("Required attr machine_name missing")
        return machine

    def _compiler(self, metadata):
        compiler = self.create_element(cim.Compiler)
        for required in ["name", "version"]:
            try:
                setattr(
                    compiler, required, metadata["compiler_%s" % required])
            except KeyError:
                raise DaoContractException(
                    "Required attr %s missing" % required)
        return compiler


class ResponsibleParty(Element):

    def __init__(self, dao, id_dao, attribute):
        super(ResponsibleParty, self).__init__(dao, id_dao, attribute)

    def container_metadata(self, parent):
        self.dao.container_metadata(parent.dao)
        return

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.ResponsibleParty)
        optional = [
            "email", "address", "url", "individual_name", "organisation_name"]
        self.populate_attr(element, metadata, [], optional)
        return element

    def add_to_doc(self, doc, model_element):
        doc.responsible_parties.append(model_element)
        return


class StandardName(Element):

    def __init__(self, dao, id_dao, attribute):
        super(StandardName, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.StandardName)
        required = ["value"]
        self.populate_attr(element, metadata, required, [])
        setattr(element, "is_open", True)
        return element

    def add_to_doc(self, doc, model_element):
        # Standard names are made and added to elements internally,
        # rather than being made and added as standalone elements.
        return
