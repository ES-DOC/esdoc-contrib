from datetime import date
from mock import Mock
import unittest

import pyesdoc.ontologies.cim.v1 as cim

from dao.dao_exception import DaoContractException
from dao.id_dao import Null
from elements import Citation, DocReference, Platform, \
    ResponsibleParty, StandardName, ReferenceByName
import shared


class TestCitation(unittest.TestCase):

    def setUp(self):
        self.element = Citation(None, Null(), shared.config())
        self.valid_metadata = {
            "title": "Foo (2014)", "date": date(2014, 1, 1)}

    def test_cim_element(self):
        # Add an optional attribute.
        self.valid_metadata["location"] = "http://foo.pdf"
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.title, "Foo (2014)")

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.ModelComponent)
        element = shared.make_empty_component(cim.Citation)
        self.element.add_to_doc(doc, element)
        self.assertEqual(len(doc.citations), 1)


class TestDocReference(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.attribute = {
            "institute": "mohc", "project": "cmip5",
            "link": {"type": "Platform", "name": "IBM Power 6_Other"},
            "link_to": "platform"}
        self.element = DocReference(None, self.mock_id_dao, self.attribute)
        self.valid_metadata = {"id": "ref-id-in-here"}

    def test_attr_for_constraint_in_place(self):
        self.assertEqual(self.element.constraint, self.attribute["link"])

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.id, self.valid_metadata["id"])
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.Deployment)
        element = shared.make_empty_component(cim.DocReference)
        self.element.link_to = "platform_reference"
        self.element.add_to_doc(doc, element)
        self.assertEqual(doc.platform, None)
        self.assertEqual(doc.platform_reference, element)


class TestReferenceByName(unittest.TestCase):

    def setUp(self):
        config = shared.config()
        config["link_to"] = "requirements_references"
        self.element = ReferenceByName(None, Null(), config)
        self.valid_metadata = {
            "name": "init_continuation", "type": "InitialCondition",
            "description":
            "initial conditions from specific date and experiment"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.name, "init_continuation")
        self.assertEqual(type(cim_element).__name__, "DocReference")

    def test_cim_element_contract(self):
        # We have only optional attr, but we should get a value for at
        # least one of them.
        no_metadata = {}
        self.assertRaises(
            DaoContractException, self.element.cim_element,
            no_metadata, [])

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.Conformance)
        cim_element = shared.make_element(self)
        self.assertEqual(len(doc.requirements_references), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.requirements_references), 1)


class TestPlatform(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = Platform(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {
            "short_name": "Not provided",
            "machine_name": "Not provided",
            "compiler_name": "Not provided",
            "compiler_version": "Not provided"}

    def test_cim_element(self):
        self.valid_metadata["long_name"] = "Not provided"
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.short_name, "Not provided")
        self.assertEqual(len(cim_element.units), 1)
        self.mock_id_dao.add_id.assert_called_once_with(
            "Platform", self.valid_metadata["short_name"],
            cim_element.meta.id)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.DocumentSet)
        element = shared.make_empty_component(cim.Platform)
        self.element.add_to_doc(doc, element)
        self.assertEqual(doc.platform, element)


class TestResponsibleParty(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = ResponsibleParty(
            None, self.mock_id_dao, shared.config())
        # Everything is optional!
        self.valid_metadata = {}

    def test_cim_element(self):
        self.valid_metadata = {
            "individual_name": "Dr Bill Collins",
            "address": "Fitzroy Road,Exeter,Devon,EX1 3PB,UK",
            "organisation_name": "Met Office Hadley Centre",
            "email": "bill.collins@metoffice.gov.uk",
            "url": "www.metoffice.gov.uk"}
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.url, "www.metoffice.gov.uk")
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.ModelComponent)
        cim_element = shared.make_empty_component(cim.ResponsibleParty)
        self.assertEqual(len(doc.responsible_parties), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.responsible_parties), 1)


class TestStandardName(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = StandardName(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"value": "r2i1p1"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.value, self.valid_metadata["value"])
        self.assertTrue(cim_element.is_open)
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)


if __name__ == "__main__":
    unittest.main()
