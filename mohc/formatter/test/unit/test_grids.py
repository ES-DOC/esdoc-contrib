import unittest
from mock import Mock

import pyesdoc.ontologies.cim.v1 as cim

import shared
from elements import GridSpec, GridMosaic, GridTile


class TestGridSpec(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = GridSpec(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"short_name": "UM ATM N96L38 Grid"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertEqual(
            cim_element.short_name, self.valid_metadata["short_name"])
        self.mock_id_dao.add_id.assert_called_once_with(
            "GridSpec", "UM ATM N96L38 Grid", cim_element.meta.id)

    def test_cim_element_contract(self):
        shared.test_cim_element_contract(self)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.DocumentSet)
        cim_element = shared.make_empty_component(cim.GridSpec)
        self.assertEqual(len(doc.grids), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.grids), 1)


class TestGridMosaic(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        config = shared.config()
        config["esm_type"] = "model"
        self.element = GridMosaic(None, self.mock_id_dao, config)
        self.valid_metadata = {"type": "regular_lat_lon"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertIsInstance(cim_element, cim.GridMosaic)
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_special_method(self):
        self.assertTrue(self.element.is_mosaic())

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.GridSpec)
        cim_element = shared.make_empty_component(cim.GridMosaic)
        self.assertEqual(len(doc.esm_model_grids), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.esm_model_grids), 1)

    def test_add_mosaic_to_mosaic(self):
        doc = shared.make_empty_component(cim.GridMosaic)
        cim_element = shared.make_empty_component(cim.GridMosaic)
        cim_element.is_leaf = False
        self.assertEqual(len(doc.mosaics), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.mosaics), 1)


class TestGridTile(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = GridTile(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"discretization_type": "logically_rectangular"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertIsInstance(cim_element, cim.GridTile)
        self.assertEqual(self.mock_id_dao.add_id.called, False)

    def test_expected_exception(self):
        try:
            is_mosaic = self.element.is_mosaic()
            fail("Should get an attribute error!")
        except AttributeError:
            self.assertTrue(True)

    def test_add_to_doc(self):
        doc = shared.make_empty_component(cim.GridMosaic)
        cim_element = shared.make_empty_component(cim.GridTile)
        self.assertEqual(len(doc.tiles), 0)
        self.element.add_to_doc(doc, cim_element)
        self.assertEqual(len(doc.tiles), 1)


if __name__ == "__main__":
    unittest.main()
