# -*- coding: utf-8 -*-

from mock import Mock
import unittest

from dao.id_dao import DocIdDao
from dao.dao_exception import DaoConnectionException, DaoMetadataException


class TestLDocIdDao(unittest.TestCase):

    def setUp(self):
        self.dao = DocIdDao()
        self.dao.id = {
            "ModelComponent:HadGEM2-ES": "mod1",
            "ModelComponent:HadGEM2-ES:Atmosphere": "mod1.1",
            "NumericalExperiment:rcp85": "id2",
            "DataObject:name1": "id23",
            "DataObject:name2": "id24",
            "DataObject:name3": "id25"}

    def test_in_memory_id(self):
        constraint = self._constraint("NumericalExperiment", "rcp85")
        metadata = self.dao.metadata(constraint)
        self.assertEqual(metadata["id"], "id2")

    def test_picks_up_sub_models(self):
        constraint = self._constraint(
            "ModelComponent", "HadGEM2-ES:Atmosphere")
        metadata = self.dao.metadata(constraint)
        self.assertEqual(metadata["id"], "mod1.1")

    def test_metadata_error_for_missing_id(self):
        constraint = self._constraint("MST3K", "TomServo")
        self.assertRaises(
            DaoMetadataException, self.dao.metadata, constraint)

    def test_daos_for_node(self):
        fake_container_dao = Mock()
        fake_return = ["name1", "name2", "name3"]
        fake_container_dao.name_for_reference.return_value = fake_return
        daos = self.dao.daos_for_node({
            "type": "DataObject", "name": "",
            "container_dao": fake_container_dao})
        self.assertEqual(len(daos), 3)

    def _constraint(self, type, name):
        return {"type": type, "name": name}


if __name__ == "__main__":
    unittest.main()
