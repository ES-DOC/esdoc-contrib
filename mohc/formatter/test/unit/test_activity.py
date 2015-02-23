# -*- coding: utf-8 -*-

from datetime import datetime
import unittest
from mock import Mock

import pyesdoc.ontologies.cim.v1 as cim

import shared
from elements import NumericalExperiment, NumericalRequirement, \
    SimulationRun, Ensemble, EnsembleMember, Conformance


class TestNumericalExperiment(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = NumericalExperiment(
            None, self.mock_id_dao, shared.config())
        self.valid_metadata = {
            "calendar": "360_day",
            "long_name": "4.2 HadGEM2-ES RCP8.5",
            "short_name": "rcp85"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.short_name, "rcp85")
        self.mock_id_dao.add_id.assert_called_once_with(
            "NumericalExperiment", "rcp85", cim_element.meta.id)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.DocumentSet)
        cim_element = shared.make_empty_component(cim.NumericalExperiment)
        self.assertEqual(doc.experiment, None)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(cim_element, doc.experiment)


class TestNumericalRequirement(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = NumericalRequirement(
            None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"type": "initial", "name": "init_continuation"}

    def test_cim_element(self):
        self.valid_metadata["description"] = "some description text"
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.name, "init_continuation")
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.NumericalExperiment)
        element = shared.make_empty_component(cim.NumericalRequirement)
        self.assertEqual(len(doc.requirements), 0)
        self.element.add_to_doc(doc, element)
        self.assertEqual(len(doc.requirements), 1)


class TestSimulationRun(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = SimulationRun(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {
            "long_name": "Future scenario - 8.5",
            "short_name": "rcp85", "calendar": "360_day",
            "start_date": datetime(2005, 12, 1),
            "end_date": datetime(2101, 1, 1)}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.short_name, "rcp85")
        self.assertEqual(
            cim_element.date_range.start,
            self.valid_metadata["start_date"])
        self.mock_id_dao.add_id.assert_called_once_with(
            "SimulationRun", self.valid_metadata["short_name"],
            cim_element.meta.id)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.DocumentSet)
        cim_element = shared.make_empty_component(cim.SimulationRun)
        self.assertEqual(doc.simulation, None)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(doc.simulation, cim_element)


class TestEnsemble(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = Ensemble(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {
            "long_name": "representative concentration pathway 8.5",
            "short_name": "rcp85",
            "type": "initial condition"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.short_name, "rcp85")
        self.mock_id_dao.add_id.assert_called_once_with(
            "Ensemble", "rcp85", cim_element.meta.id)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.DocumentSet)
        cim_element = shared.make_empty_component(cim.Ensemble)
        self.assertEqual(len(doc.ensembles), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(doc.ensembles[0], cim_element)


class TestEnsembleMember(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = EnsembleMember(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {
            "short_name": "rcp85_01",
            "long_name": "rcp85 ensemble - element 1"}

    def test_cim_element(self):
        self.valid_metadata["standard_name"] = "r1i1p1"
        self.valid_metadata["description"] = "filler"
        cim_element = shared.make_element(self)
        self.assertEqual(len(cim_element.ensemble_ids), 1)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.Ensemble)
        cim_element = shared.make_empty_component(cim.EnsembleMember)
        self.assertEqual(len(doc.members), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(doc.members[0], cim_element)


class TestConformance(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = Conformance(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"is_conformant": True}

    def test_cim_element(self):
        self.valid_metadata["type"] = "config"
        cim_element = shared.make_element(self)
        self.assertTrue(cim_element.is_conformant)
        self.assertEqual(cim_element.type, "config")
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.SimulationRun)
        cim_element = shared.make_empty_component(cim.Conformance)
        self.assertEqual(len(doc.conformances), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.conformances), 1)


if __name__ == "__main__":
    unittest.main()
