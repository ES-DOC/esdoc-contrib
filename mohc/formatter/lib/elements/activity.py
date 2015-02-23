# -*- coding: utf-8 -*-

import pyesdoc.ontologies.cim.v1 as cim

from element import Element
from dao.dao_exception import DaoContractException
from shared import StandardName


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class NumericalExperiment(Element):

    def __init__(self, dao, id_dao, attribute):
        super(NumericalExperiment, self).__init__(dao, id_dao, attribute)

    def daos_for_node(self, constraint):
        return [self.dao]

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.NumericalExperiment)
        required = ["short_name", "long_name", "calendar"]
        optional = ["description"]
        self.populate_attr(element, metadata, required, optional)
        self.id_name = element.short_name
        self.id_dao.add_id(
            "NumericalExperiment", self.id_name, element.meta.id)
        return element

    def add_to_doc(self, doc, model_element):
        doc.experiment = model_element
        return


class NumericalRequirement(Element):

    def __init__(self, dao, id_dao, attribute):
        super(NumericalRequirement, self).__init__(dao, id_dao, attribute)

    def container_metadata(self, parent_node):
        self.dao.container_metadata(parent_node.dao)
        return

    def cim_element(self, metadata, leaves):
        if "type" not in metadata:
            raise DaoContractException(
                "Attribute type not in NumericalRequirement")
        element_type = {
            "initial": cim.InitialCondition,
            "spatiotemporal": cim.SpatioTemporalConstraint,
            "boundary": cim.BoundaryCondition}
        if metadata["type"] not in element_type:
            raise DaoContractException(
                "Unknown numerical requirement type %s" % metadata["type"])
        element = self.create_element(element_type[metadata["type"]])
        required = ["name"]
        optional = ["description"]
        self.populate_attr(element, metadata, required, optional)
        return element

    def add_to_doc(self, doc, model_element):
        doc.requirements.append(model_element)
        return


class SimulationRun(Element):

    def __init__(self, dao, id_dao, attribute):
        super(SimulationRun, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.SimulationRun)
        required = ["long_name", "short_name"]
        optional = ["description"]
        self.populate_attr(element, metadata, required, optional)
        try:
            element.date_range = self._date_range(
                metadata["start_date"], metadata["end_date"])
            element.calendar = self.calendar(metadata["calendar"])
        except KeyError:
            raise DaoContractException("Required attr missing")
        self.id_dao.add_id(
            "SimulationRun", metadata["short_name"], element.meta.id)
        return element

    def add_to_doc(self, doc, model_element):
        doc.simulation = model_element
        return

    def _date_range(self, start, end):
        date_range = self.create_element(cim.ClosedDateRange)
        date_range.start = start
        date_range.end = end
        return date_range


class Ensemble(Element):

    def __init__(self, dao, id_dao, attribute):
        super(Ensemble, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.Ensemble)
        required = ["long_name", "short_name"]
        optional = []
        self.populate_attr(element, metadata, required, optional)
        try:
            element.types.append(metadata["type"])
        except KeyError:
            raise DaoContractException("Required attr missing")
        self.id_name = element.short_name
        self.id_dao.add_id("Ensemble", self.id_name, element.meta.id)
        return element

    def add_to_doc(self, doc, model_element):
        doc.ensembles.append(model_element)
        return


class EnsembleMember(Element):

    def __init__(self, dao, id_dao, attribute):
        super(EnsembleMember, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.EnsembleMember)
        required = ["short_name", "long_name"]
        optional = ["description"]
        self.populate_attr(element, metadata, required, optional)
        try:
            standard_name = StandardName(
                None, None,
                {"institute": self.institute, "project": self.project})
            name = standard_name.cim_element(
                {"value": metadata["standard_name"]}, [])
            element.ensemble_ids.append(name)
        except KeyError:
            # Ensemble id is optional.
            pass
        return element

    def add_to_doc(self, doc, model_element):
        doc.members.append(model_element)
        return


class Conformance(Element):

    def __init__(self, dao, id_dao, attribute):
        super(Conformance, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.Conformance)
        required = ["is_conformant"]
        optional = ["description", "type"]
        self.populate_attr(element, metadata, required, optional)
        return element

    def add_to_doc(self, doc, model_element):
        doc.conformances.append(model_element)
        return
