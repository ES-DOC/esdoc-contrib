# -*- coding: utf-8 -*-

from datetime import date
from mock import Mock
import unittest

import pyesdoc.ontologies.cim.v1 as cim

from elements import Deployment, Model, SubModel, ComponentProperty
from dao.id_dao import Null
import shared


class TestDeployment(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = Deployment(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertIsInstance(cim_element, cim.Deployment)
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.SimulationRun)
        element = shared.make_empty_component(cim.Deployment)
        self.assertEqual(len(doc.deployments), 0)
        self.element.add_to_doc(doc, element)
        self.assertEqual(len(doc.deployments), 1)


class TestModel(unittest.TestCase):

    def setUp(self):
        self.element = Model(None, Null(), shared.config())
        self.valid_metadata = {"short_name": "HadGEM2-ES"}

    def test_cim_element(self):
        # Pop in some optional attributes.
        self.valid_metadata = {
            "short_name": "HadGEM2-ES",
            "long_name": "HadGEM2-ES (2009) ...",
            "description": "Big clever model with lots of bits",
            "release_date": date(2009, 11, 1)}
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.short_name, "HadGEM2-ES")

    def test_docinfo_ok(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.meta.institute, "mohc")
        self.assertEqual(cim_element.meta.project, "cmip5")

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        pass


class TestSubModel(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = SubModel(None, self.mock_id_dao, shared.config())
        self.element.container_id_name = "HadGEM2-ES"
        self.valid_metadata = {"short_name": "Aerosols", "type": "Aerosols"}

    def test_cim_element(self):
        self.valid_metadata["long_name"] = "Aerosols and stuff"
        self.valid_metadata["description"] = "Detailed description"
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.short_name, "Aerosols")
        self.assertEqual(len(cim_element.properties), 0)
        self.mock_id_dao.add_id.assert_called_once_with(
            "ModelComponent", "HadGEM2-ES:Aerosols", cim_element.meta.id)

    @unittest.expectedFailure
    def test_cim_element_that_causes_trouble(self):
        self.valid_metadata = {
            "long_name": "Atmosphere",
            "description": "0.44\xb0x0.44\xb0",
            "short_name": "Atmosphere",
            "type": "Atmosphere"}
        for attribute in self.valid_metadata:
            if isinstance(self.valid_metadata[attribute], str):
                self.valid_metadata[attribute] = unicode(
                    self.valid_metadata[attribute].decode("latin-1"))
        cim_element = shared.make_element(self)
        try:
            xml = pyesdoc.encode(cim_element, pyesdoc.ENCODING_XML)
            self.assertTrue(True)
        except:
            self.fail("pyesdoc encoding to XML failed")

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.ModelComponent)
        cim_element = shared.make_empty_component(cim.ModelComponent)
        self.assertEqual(len(doc.sub_components), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.sub_components), 1)


class TestComponentProperty(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = ComponentProperty(
            None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"short_name": "BasicApproximations"}

    def test_cim_element(self):
        # Add some useful optional attributes.
        self.valid_metadata = {
            "short_name": "BasicApproximations",
            "description": "Description of the basic approx...",
            "units": "",
            "values": ["Modal scheme", "mass as a tracer", "number inferred"]}
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.short_name, "BasicApproximations")
        self.assertEqual(len(cim_element.values), 3)
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.ModelComponent)
        element = shared.make_empty_component(cim.ComponentProperty)
        self.assertEqual(len(doc.properties), 0)
        self.element.add_to_doc(doc, element)
        self.assertEqual(len(doc.properties), 1)


if __name__ == "__main__":
    unittest.main()
