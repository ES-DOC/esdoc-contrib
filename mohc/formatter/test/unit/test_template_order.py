import unittest

import elements
import template


class TestTemplateOrder(unittest.TestCase):

    def setUp(self):
        self.dao = {"NullDao": {}}
        self.cfg = {
            "global": {
                "institute": "mohc",
                "project": "cmip5",
                "daopkg": "dao.null_dao"}}
        self.dao_env = {"model": "HadGEM2-ES"}
        self.template = {}

    def test_no_ref(self):
        self.template["DocumentSet"] = {
            "dao": self.dao,
            "contents": [{
                "SimulationRun": {
                    "dao": self.dao,
                    "contents": []}}, {
                "Platform": {
                    "dao": self.dao,
                    "contents": []}}]}
        tree = template.doc_builder(self.template, self.dao_env, self.cfg)
        self.assertIsInstance(
            tree["contents"][0]["node"], elements.SimulationRun)
        self.assertIsInstance(
            tree["contents"][1]["node"], elements.Platform)

    def test_ref_in_wrong_place(self):
        self.template["DocumentSet"] = {
            "dao": self.dao,
            "contents": [{
                "SimulationRun": {
                    "dao": self.dao,
                    "contents": [{
                        "Deployment": {
                            "dao": self.dao,
                            "contents": [{
                                "DocReference": {
                                    "link": {
                                        "type": "Platform",
                                        "name": ""},
                                    "link_to": "foo"}}]}}]}}, {
                "Platform": {"dao": self.dao}}]}
        tree = template.doc_builder(self.template, self.dao_env, self.cfg)
        self.assertEqual(len(tree["contents"]), 2)
        self.assertIsInstance(
            tree["contents"][0]["node"], elements.Platform)
        self.assertIsInstance(
            tree["contents"][1]["node"], elements.SimulationRun)

    def test_ref_in_right_place(self):
        self.template["DocumentSet"] = {
            "dao": self.dao,
            "contents": [{
                "Platform": {"dao": self.dao}}, {
                    "SimulationRun": {
                        "dao": self.dao,
                        "contents": [{
                            "Deployment": {
                                "dao": self.dao,
                                "contents": [{
                                    "DocReference": {
                                        "link": {
                                            "type": "Platform",
                                            "name": ""},
                                        "link_to": "foo"}}]}}]}}]}
        tree = template.doc_builder(self.template, self.dao_env, self.cfg)
        self.assertEqual(len(tree["contents"]), 2)
        self.assertIsInstance(
            tree["contents"][0]["node"], elements.Platform)
        self.assertIsInstance(
            tree["contents"][1]["node"], elements.SimulationRun)

    def test_realistic_template_in_order(self):
        self.template["DocumentSet"] = self._experiment_template()
        tree = template.doc_builder(self.template, self.dao_env, self.cfg)
        self.assertEqual(len(tree["contents"]), 6)
        expected = [
            elements.NumericalExperiment, elements.DataObject,
            elements.Platform, elements.SimulationRun,
            elements.Ensemble, elements.GridSpec]
        for idx, leaf in enumerate(tree["contents"]):
            self.assertIsInstance(leaf["node"], expected[idx])

    def test_realistic_template_out_of_order(self):
        self.template["DocumentSet"] = self._experiment_template()
        contents = self.template["DocumentSet"]["contents"]
        # Put SimRun at the start of the list - it has three different
        # references, so that will require a big reorg to get right.
        # Ensemble refers to SimRun, so the change will ripple out.
        contents[0], contents[3] = contents[3], contents[0]
        tree = template.doc_builder(self.template, self.dao_env, self.cfg)
        self.assertEqual(len(tree["contents"]), 6)
        actual_position = {}
        for idx, leaf in enumerate(tree["contents"]):
            leaf_type = type(leaf["node"]).__name__
            actual_position[leaf_type] = idx
        for referred_to in ["NumericalExperiment", "Platform", "DataObject"]:
            self.assertTrue(
                actual_position[referred_to] <
                actual_position["SimulationRun"])
        for referred_to in ["NumericalExperiment", "SimulationRun"]:
            self.assertTrue(
                actual_position[referred_to] < actual_position["Ensemble"])

    def _experiment_template(self):
        expt = {
            "dao": {"NullDao": {}},
            "contents": [{
                "NumericalExperiment": {
                    "dao": self.dao,
                    "contents": [{
                        "NumericalRequirement": {"dao": self.dao}}]}}, {
                "DataObject": {"dao": self.dao}}, {
                    "Platform": {"dao": self.dao}}, {
                "SimulationRun": {
                    "dao": self.dao,
                    "contents": [{
                        "ResponsibleParty": {"dao": self.dao}}, {
                        "Conformance": {
                            "dao": self.dao,
                            "contents": [{
                                "DocReference": {
                                    "link": {
                                        "type": "DataObject",
                                        "name": ""},
                                    "link_to": "sources_references"}}]}}, {
                        "Deployment": {
                            "dao": self.dao,
                            "contents": [{
                                "DocReference": {
                                    "link": {
                                        "type": "Platform",
                                        "name": ""},
                                    "link_to": "platform_reference"}}]}}, {
                        "DocReference": {
                            "link": {
                                "type": "NumericalExperiment",
                                "name": ""},
                            "link_to": "supports_references"}}]}}, {
                "Ensemble": {
                    "dao": self.dao,
                    "contents": [{
                        "DocReference": {
                             "link": {
                                 "type": "NumericalExperiment",
                                 "name": ""},
                             "link_to": "supports_reference"}}, {
                        "EnsembleMember": {
                            "dao": self.dao,
                            "contents": [{
                                "DocReference": {
                                    "link": {
                                        "type": "SimulationRun",
                                        "name": ""},
                                    "link_to": "sim_ref"}}]}}]}}, {
                "GridSpec": {
                    "dao": self.dao,
                    "contents": [{
                        "GridMosaic": {
                            "dao": self.dao,
                            "esm_type": "model",
                            "contents": [{
                                "GridTile": {"dao": self.dao}}]}}]}}]}
        return expt


if __name__ == "__main__":
    unittest.main()
