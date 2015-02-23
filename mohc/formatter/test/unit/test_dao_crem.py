# -*- coding: utf-8 -*-

from datetime import datetime
import unittest

import dao.crem
from dao.dao_exception import DaoMetadataException


class TestDao(unittest.TestCase):

    def setUp(self):
        self.db_env = {}
        self.project = "CMIP5"
        self.model_constraint = {"id": 7}
        self.model_name = "HadGEM2-ES"
        self.model_table = dao.crem.DbTable("7", "model")
        self.experiment = "rcp85"
        self.experiment_constraint = {"id": "20"}

    def test_connect(self):
        crem_dao = self._make_dao(dao.crem.CremDao)
        try:
            db = crem_dao.connect()
            self.assertTrue(True)
        except DaoMetadataException:
            self.fail("Can't connect to database")

    def test_single_row(self):
        crem_dao = self._make_dao(dao.crem.CremDao)
        query = (
            "SELECT idtblmodel as id FROM tblmodel WHERE "
            "shortname = %s")
        record = crem_dao.single_row_query(query, (self.model_name, ))
        self.assertEqual(len(record), 1)
        self.assertEqual(record["id"], self.model_constraint["id"])

    def test_multi_row(self):
        crem_dao = self._make_dao(dao.crem.CremDao)
        query = (
            "SELECT * FROM tblmodelcomponent WHERE modelID = %s "
            "AND parentComponentID is NULL AND level = %s")
        records = crem_dao.multi_row_query(query, (7, 1))
        self.assertEqual(len(records), 8)

    def test_model(self):
        model_dao = self._make_dao(dao.crem.ModelDao)
        model_dao.model = self.model_name
        metadata = model_dao.metadata({})
        self.assertEqual(metadata["short_name"], "HadGEM2-ES")
        self.assertEqual(model_dao.id(), self.model_constraint["id"])

    def test_model_no_name(self):
        model_dao = self._make_dao(dao.crem.ModelDao)
        self.assertRaises(DaoMetadataException, model_dao.metadata, {})

    def test_responsible_party(self):
        rp_dao = self._make_dao(dao.crem.ResponsiblePartyDao)
        rp_dao.rp_id = 22
        rp_dao.parent_table = self.model_table
        metadata = rp_dao.metadata({})
        self.assertEqual(metadata["individual_name"], "Dr Bill Collins")

    def test_rp_daos_for_node(self):
        rp_dao = self._make_dao(dao.crem.ResponsiblePartyDao)
        rp_dao.parent_table = self.model_table
        daos = rp_dao.daos_for_node({})
        self.assertEqual(len(daos), 1)

    def test_rp_daos_for_sub_model_node(self):
        rp_dao = self._make_dao(dao.crem.ResponsiblePartyDao)
        rp_dao.comp_id = 51
        rp_dao.parent_table = dao.crem.DbTable("51", "component")
        daos = rp_dao.daos_for_node({})
        self.assertEqual(len(daos), 1)
        self.assertEqual(daos[0].rp_id, 27)

    def test_citation_metadata(self):
        cite_dao = self._make_dao(dao.crem.CitationDao)
        cite_dao.cite_id = 5
        cite_dao.parent_table = self.model_table
        metadata = cite_dao.metadata({})
        self.assertEqual(metadata["title"], "Collins W.J.  (2008)")
        expected_date = datetime(2008, 1, 1, 0, 0)
        self.assertEqual(metadata["date"], expected_date)

    def test_ctation_daos_for_node(self):
        cite_dao = self._make_dao(dao.crem.CitationDao)
        cite_dao.parent_table = self.model_table
        daos = cite_dao.daos_for_node({})
        self.assertEqual(len(daos), 2)

    def test_model_ref_dao(self):
        model_ref_dao = self._make_dao(dao.crem.ModelComponentRefDao)
        model_ref_dao.model_id = self.model_constraint["id"]
        metadata = model_ref_dao.metadata({})
        self.assertEqual(metadata["name"], self.model_name)
        self.assertEqual(metadata["type"], "ModelComponent")

    def test_modeL_ref_daos_for_node(self):
        model_ref_dao = self._make_dao(dao.crem.ModelComponentRefDao)
        model_ref_dao.project = self.project
        model_ref_dao.experiment = self.experiment
        model_ref_dao.model = self.model_name
        daos = model_ref_dao.daos_for_node({})
        self.assertEqual(len(daos), 1)
        self.assertEqual(daos[0].model_id, self.model_constraint["id"])

    def test_sub_model_daos_for_node(self):
        sub_model_dao = self._make_dao(dao.crem.SubModelDao)
        sub_model_dao.parent_table = self.model_table
        daos = sub_model_dao.daos_for_node(self.model_constraint)
        self.assertEqual(len(daos), 8)

    def test_sub_model(self):
        sub_model_dao = self._make_dao(dao.crem.SubModelDao)
        sub_model_dao.comp_id = 51
        metadata = sub_model_dao.metadata({})
        self.assertEqual(metadata["short_name"], "Aerosols")

    def test_sub_model_standalone(self):
        sub_model_dao = self._make_dao(dao.crem.SubModelDao)
        sub_model_dao.model = self.model_name
        sub_model_dao.submodel = "Aerosols"
        metadata = sub_model_dao.metadata({})
        self.assertEqual(sub_model_dao.comp_id, 51)

    def test_property(self):
        prop_dao = self._make_dao(dao.crem.ComponentPropertyDao)
        prop_dao.prop_id = "38"
        metadata = prop_dao.metadata({})
        self.assertEqual(len(metadata["values"]), 3)
        self.assertEqual(metadata["short_name"], "BasicApproximations")

    def test_property_requires_prop_id(self):
        prop_dao = self._make_dao(dao.crem.ComponentPropertyDao)
        self.assertRaises(DaoMetadataException, prop_dao.metadata, {})

    def test_numerical_experiment(self):
        ne_dao = self._make_dao(dao.crem.NumericalExperimentDao)
        ne_dao.experiment = self.experiment
        ne_dao.project = self.project
        ne_dao.model = self.model_name
        metadata = ne_dao.metadata({})
        self.assertEqual(metadata["short_name"], self.experiment)
        self.assertEqual(metadata["long_name"], "4.2 HadGEM2-ES RCP8.5")
        self.assertEqual(metadata["calendar"], "360_day")
        self.assertTrue("description" in metadata)
        self.assertEqual(ne_dao.expt_name, self.experiment)
        self.assertEqual(ne_dao.id(), 20)

    def test_numerical_requirement_metadata(self):
        nr_dao = self._make_dao(dao.crem.NumericalRequirementDao)
        nr_dao.id = "7"
        metadata = nr_dao.metadata({})
        self.assertEqual(metadata["name"], "forc_co2c_prpi")
        self.assertEqual(metadata["type"], "boundary")
        self.assertEqual(
            metadata["description"],
            "prescribed  pre-industrial concentrations of CO2")

    def test_numerical_requirement_nodes(self):
        nr_dao = self._make_dao(dao.crem.NumericalRequirementDao)
        nr_dao.parent_expt_name = self.experiment
        daos = nr_dao.daos_for_node({})
        self.assertEqual(len(daos), 12)

    def test_data_object_metadata(self):
        do_dao = self._make_dao(dao.crem.DataObjectDao)
        do_dao.id = 16
        metadata = do_dao.metadata({})
        self.assertEqual(metadata["acronym"], "well_mixed_gas_CH4")

    def test_data_object_nodes(self):
        do_dao = self._make_dao(dao.crem.DataObjectDao)
        daos = do_dao.daos_for_node(self.experiment_constraint)
        self.assertEqual(len(daos), 24)

    def test_platform(self):
        platform_dao = self._make_dao(dao.crem.PlatformDao)
        metadata = platform_dao.metadata({})
        self.assertEqual(metadata["short_name"], "Not provided")

    def test_simulation_run(self):
        simulation_dao = self._make_dao(dao.crem.SimulationRunDao)
        metadata = simulation_dao.metadata({"id": "20"})
        self.assertEqual(metadata["short_name"], self.experiment)
        self.assertEqual(metadata["calendar"], "360_day")
        self.assertEqual(metadata["start_date"], datetime(2005, 12, 1))
        self.assertEqual(metadata["end_date"], datetime(2101, 1, 1))

    def test_ensemble(self):
        ensemble_dao = self._make_dao(dao.crem.EnsembleDao)
        metadata = ensemble_dao.metadata(self.experiment_constraint)
        self.assertEqual(metadata["short_name"], self.experiment)
        self.assertEqual(
            metadata["long_name"], "4.2 HadGEM2-ES RCP8.5")
        self.assertEqual(metadata["type"], "initial condition")

    def test_ensemble_member(self):
        ensemble_member_dao = self._make_dao(dao.crem.EnsembleMemberDao)
        ensemble_member_dao.sim_id = 517
        metadata = ensemble_member_dao.metadata({})
        self.assertEqual(metadata["standard_name"], "r2i1p1")
        self.assertEqual(metadata["short_name"], "rcp85_02")
        self.assertEqual(metadata["description"], "Not provided by CREM")

    def test_ensemble_member_daos(self):
        ensemble_member_dao = self._make_dao(dao.crem.EnsembleMemberDao)
        daos = ensemble_member_dao.daos_for_node(self.experiment_constraint)
        self.assertEqual(len(daos), 4)

    def test_conformance(self):
        conformance_dao = self._make_dao(dao.crem.ConformanceDao)
        conformance_dao.conf_id = 195
        metadata = conformance_dao.metadata({})
        self.assertTrue(metadata["is_conformant"])
        self.assertEqual(metadata["type"], "input")

    def test_conformance_daos_for_node(self):
        conformance_dao = self._make_dao(dao.crem.ConformanceDao)
        conformance_dao.connect_env = {"type": "data_source"}
        daos = conformance_dao.daos_for_node(self.experiment_constraint)
        self.assertEqual(len(daos), 8)
        self.assertEqual(daos[0].conf_id, 195)
        self.assertEqual(daos[0].reqt_id, 12)
        conformance_dao = self._make_dao(dao.crem.ConformanceDao)
        daos = conformance_dao.daos_for_node(self.experiment_constraint)
        self.assertEqual(len(daos), 3)
        self.assertEqual(daos[0].conf_id, 196)
        self.assertEqual(daos[0].reqt_id, 15)

    def test_conformance_name_for_reference(self):
        conformance_dao = self._make_dao(dao.crem.ConformanceDao)
        conformance_dao.conf_id = 195
        conformance_dao.expt_id = self.experiment_constraint["id"]
        name = conformance_dao.name_for_reference({"type": "DataObject"})
        self.assertEqual(name[0], "volcanic_optical_thickness")

    def test_num_req_ref_dao(self):
        ref_dao = self._make_dao(dao.crem.NumericalRequirementRefDao)
        ref_dao.reqt_id = 15
        metadata = ref_dao.metadata({})
        self.assertEqual(metadata["name"], "init_continuation")
        self.assertEqual(metadata["type"], "InitialCondition")

    def test_num_req_ref_daos_for_node(self):
        ref_dao = self._make_dao(dao.crem.NumericalRequirementRefDao)
        ref_dao.conf_id = 196
        daos = ref_dao.daos_for_node(self.experiment_constraint)
        self.assertEqual(len(daos), 1)
        self.assertEqual(daos[0].reqt_id, 15)

    def test_grid_spec(self):
        grid_spec_dao = self._make_dao(dao.crem.GridSpecDao)
        metadata = grid_spec_dao.metadata(self.experiment_constraint)
        self.assertEqual(metadata["short_name"], "Standard HadGEM Grid System")

    def test_grid_mosaic(self):
        mosaic_dao = self._make_dao(dao.crem.GridMosaicDao)
        mosaic_dao.mosaic_id = 1
        metadata = mosaic_dao.metadata({})
        self.assertEqual(metadata["short_name"], "UM ATM N96L38 Grid")
        self.assertEqual(metadata["type"], "regular_lat_lon")

    def test_grid_mosaic_daos(self):
        mosaic_dao = self._make_dao(dao.crem.GridMosaicDao)
        mosaic_dao.grid_sys_id = 1
        daos = mosaic_dao.daos_for_node({})
        self.assertEqual(len(daos), 2)

    def test_grid_tile(self):
        tile_dao = self._make_dao(dao.crem.GridTileDao)
        tile_dao.grid_id = 3
        metadata = tile_dao.metadata({})
        self.assertEqual(metadata["short_name"], "UM ATM N96L38 V-grid")
        self.assertTrue(metadata["is_uniform"])
        self.assertEqual(
            metadata["discretization_type"], "logically_rectangular")

    def test_grid_tile_daos(self):
        tile_dao = self._make_dao(dao.crem.GridTileDao)
        tile_dao.mosaic_id = 2
        daos = tile_dao.daos_for_node({})
        self.assertEqual(len(daos), 3)

    def test_clean_strings(self):
        crem_dao = self._make_dao(dao.crem.CremDao)
        cases = [{
            "to_clean": "first line\r\n\r\nSecond line",
            "expected": "first line\n\nSecond line"},
            {"to_clean": "first\n\n\nSecond", "expected": "first\n\nSecond"}]
        #  TODO: put this case back in when I can handle unicode properly.
        # {"to_clean": "1&#8260;3", "expected": u"1\u20443"}]
        for case in cases:
            cleaned = crem_dao.clean_string(case["to_clean"])
            self.assertEqual(case["expected"], cleaned)


    def _make_dao(self, dao_type):
        crem_dao = dao_type(self.db_env)
        crem_dao.dbname = "crememma"
        crem_dao.host = "exxar5h1"
        crem_dao.user = "ar5guest"
        return crem_dao


if __name__ == "__main__":
    unittest.main()
