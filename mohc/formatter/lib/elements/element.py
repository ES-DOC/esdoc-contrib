# -*- coding: utf-8 -*-

import abc

import pyesdoc
import pyesdoc.ontologies.cim.v1 as cim

from dao.dao_exception import DaoContractException


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class Element(object):
    """ Abstract base class for representing CIM elements. Child
    classes must implement the cim_element method (which creates an
    appropriate pyesdoc object and populates its attributes using
    provided metadata) and add_to_doc (which adds a CIM element to a
    another containing CIM element).
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, dao, id_dao, attribute):
        """ Standard initialisation code for all Element-type objects. """
        self.dao = dao
        self.id_dao = id_dao
        self.institute = str(attribute["institute"])
        self.project = str(attribute["project"])

    def add_to_doc_from_metadata(self, constraint, doc):
        """ Strategy to build a CIM element for a node and add it to a
        parent document. Calls daos_for_node to handle nodes that may
        expand to lists of nodes of the same type (e.g. Citation,
        SubModel).
        """
        daos = self.daos_for_node(constraint)
        for dao in daos:
            self.dao = dao
            cim_element = self.make_doc_from_metadata(constraint, [])
            self.add_to_doc(doc, cim_element)
        return

    def make_doc_from_metadata(self, constraint, leaves):
        """ Strategy to get metadata and use it to build a CIM element. """
        metadata = self.metadata(constraint)
        cim_element = self.cim_element(metadata, leaves)
        return cim_element

    def container_metadata(self, container):
        """ Override in a child class if an element needs access to
        some of its container's attributes or to its dao to alter its
        behaviour. For example, ModelComponent objects might need to
        know a database key for their parent model component so they
        can correctly limit their database query.
        """
        pass

    def daos_for_node(self, constraint):
        """ Called to handle elements in a template that could match
        multiple components of the same kind. For example, you may
        include "SubModel" in a template, which could match a list of
        model sub-compoents at that level.
        """
        return self.dao.daos_for_node(constraint)

    def create_element(self, element_type):
        """ Wrap pyesdoc create call. """
        return pyesdoc.create(
            element_type, project=self.project,
            institute=self.institute, version=0)

    def populate_attr(self, element, metadata, required, optional):
        """ Sets required and optional elements from metadata. """
        for req_attr in required:
            try:
                setattr(element, req_attr, metadata[req_attr])
            except KeyError:
                raise DaoContractException(
                    "Required attr %s missing" % req_attr)
        for opt_attr in optional:
            try:
                setattr(element, opt_attr, metadata[opt_attr])
            except KeyError:
                pass
        return

    def calendar(self, calendar):
        """ Map text calendar strings to appropriate CIM types. """
        known_calendar = {
            "360_day": cim.Daily360, "gregorian": cim.RealCalendar}
        if calendar in known_calendar:
            return self.create_element(known_calendar[calendar])
        else:
            raise ValueError("Unknown calendar type %s" % calendar)

    def metadata(self, constraint):
        """ Pull in metadata required to create CIM element.

        constraint can be any sort of python variable (e.g.
        dictionary, object) that your dao can use to select and return
        the required metadata.

        The dao.metadata element must return a dictionary. Key names
        should match pyesdoc attribute names (which are CIM attribute
        names converted from camel-case to python underscore names
        e.g. "short_name").
        """
        return self.dao.metadata(constraint)

    def id(self):
        """ Return database id for element. """
        return self.dao.id()

    @abc.abstractmethod
    def cim_element(self, metadata, leaves):
        """ Builds a pyesdoc CIM document element using metadata.
        metadata is a dictionary. Metadata keys are required to have
        the same names as the CIM element we're building.
        """
        return

    @abc.abstractmethod
    def add_to_doc(self, doc, cim_element):
        """ Inserts cim_element into doc in the appropriate location. """
        return
