# -*- coding: utf-8 -*-

import unittest
from mock import Mock

import pyesdoc

from elements import DocumentSet
from dao.id_dao import Null
import shared


class TestDocumentSet(unittest.TestCase):

    def setUp(self):
        self.mock_id_dao = Mock()
        self.element = DocumentSet(None, self.mock_id_dao, shared.config())
        self.valid_metadata = {"short_name": "rcp85"}

    def test_cim_element(self):
        cim_element = shared.make_element(self)
        self.assertTrue(cim_element.meta.id is not None)
        self.mock_id_dao.add_id.assert_called_once_with(
            "DocumentSet", "rcp85", cim_element.meta.id)

    def test_add_to_doc(self):
        pass


if __name__ == "__main__":
    unittest.main()
