# -*- coding: utf-8 -*-

import unittest
from mock import Mock
import shared

import pyesdoc.ontologies.cim.v1 as cim

from elements import DataObject


class TestDataObject(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = DataObject(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"acronym": "well_mixed_gas_CO2"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(cim_element.acronym, "well_mixed_gas_CO2")
        self.mock_id_dao.add_id.assert_called_once_with(
            "DataObject", "well_mixed_gas_CO2", cim_element.meta.id)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.DocumentSet)
        element = shared.make_empty_component(cim.DataObject)
        self.assertEqual(len(doc.data), 0)
        self.element.add_to_doc(doc, element)
        self.assertEqual(len(doc.data), 1)


if __name__ == "__main__":
    unittest.main()
