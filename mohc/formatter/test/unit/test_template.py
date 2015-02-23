# -*- coding: utf-8 -*-

import unittest
import StringIO

import elements
import template
from dao.crem import CremDao
from dao.id_dao import DocIdDao


class TestTemplate(unittest.TestCase):

    def setUp(self):
        self.dao = {"CremDao": {}}
        self.cfg = {
            "global": {
                "institute": "mohc",
                "project": "cmip5",
                "daopkg": "dao.crem"}}
        self.valid_config = {"dao": self.dao}

    def test_empty_template_produces_error(self):
        template_stream = self._template("")
        try:
            model_outline = template.parse_template(template_stream)
            self.fail("Empty template should raise an error")
        except template.TemplateError:
            self.assertTrue(True)

    def test_available_elements(self):
        known = template._known_elements()
        self.assertTrue(len(known) > 0)
        self.assertTrue("Model" in known)
        self.assertTrue("Element" not in known)
        self.assertTrue("NoSuchElement" not in known)

    def test_just_a_model(self):
        template_stream = self._template("""{
    "Model": {"institute": "mohc", "project": "cmip5"}
}""")
        model_outline = template.parse_template(template_stream)
        self.assertEqual(len(model_outline), 1)
        self.assertTrue("Model" in model_outline)
        self.assertEqual(model_outline["Model"]["institute"], "mohc")

    def test_template_to_doc_builder(self):
        my_template = {"Model": self.valid_config}
        doc_builder = template.doc_builder(
            my_template, {"model": "HadGEM2-ES"}, self.cfg)
        self.assertEqual(len(doc_builder), 4)
        self.assertIsInstance(doc_builder["node"], elements.Model)
        self.assertEqual(doc_builder["node"].dao.model, "HadGEM2-ES")
        self.assertEqual(len(doc_builder["contents"]), 0)

    def test_template_with_global_attribute(self):
        my_template = {"institute": "ukmo", "Model": {"dao": self.dao}}
        try:
            doc_builder = template.doc_builder(my_template, {}, self.cfg)
            self.assertEqual(doc_builder["node"].institute, "ukmo")
        except template.TemplateError as e:
            self.fail(
                "Couldn't build node with global institute: %s" % e)

    def test_template_with_contents_as_dictionary(self):
        sub_model_config = dict(self.valid_config)
        my_template = {"Model": self.valid_config}
        my_template["Model"]["contents"] = {"SubModel": sub_model_config}
        doc_builder = template.doc_builder(my_template, {}, self.cfg)
        self.assertEqual(len(doc_builder["contents"]), 1)

    def test_template_with_contents_as_list(self):
        sub_model_config = dict(self.valid_config)
        citation_config = dict(self.valid_config)
        my_template = {"Model": self.valid_config}
        my_template["Model"]["contents"] = [{
            "SubModel": sub_model_config}, {"Citation": citation_config}]
        doc_builder = template.doc_builder(my_template, {}, self.cfg)
        self.assertEqual(len(doc_builder["contents"]), 2)
        self.assertEqual(
            type(doc_builder["contents"][0]["node"]),
            elements.SubModel)
        self.assertEqual(
            type(doc_builder["contents"][1]["node"]),
            elements.Citation)

    def test_template_with_unknown_element_raises_error(self):
        my_template = {"UnknownElement": {}}
        self.assertRaises(
            template.TemplateError, template.doc_builder,
            my_template, {}, self.cfg)

    def test_valid_dao(self):
        my_template = {"Model": self.valid_config}
        doc_builder = template.doc_builder(my_template, {}, self.cfg)
        self.assertIsInstance(doc_builder["node"].dao, CremDao)

    def test_unknown_dao_raises_error(self):
        my_template = {"Model": {"dao": {"NoSuchDao": {}}}}
        self.assertRaises(
            template.TemplateError, template.doc_builder,
            my_template, {}, self.cfg)

    def test_template_needs_dao_or_link(self):
        bad_config = dict(self.valid_config)
        del bad_config["dao"]
        my_template = {"Model": bad_config}
        self.assertRaises(
            template.TemplateError, template.doc_builder, my_template,
            {}, {})
        bad_config["link"] = {"dao": {"LinkDao": {}}, "type": "", "name": ""}
        try:
            doc_builder = template.doc_builder(my_template, {}, self.cfg)
            self.assertTrue(True)
        except template.TemplateError:
            self.fail("Unexpected template error when I supplied link attr")

    def test_both_dao_and_link_raises_error(self):
        bad_config = dict(self.valid_config)
        bad_config["link"] = {}
        my_template = {"Model": bad_config}
        self.assertRaises(
            template.TemplateError, template.doc_builder, my_template,
            {}, self.cfg)

    def test_attributes(self):
        my_template = {"Model": self.valid_config}
        doc_builder = template.doc_builder(my_template, {}, self.cfg)
        self.assertEqual(doc_builder["node"].institute, "mohc")

    def test_id_dao(self):
        my_template = {"id_dao": {"DocIdDao": {}}, "Model": self.valid_config}
        doc_builder = template.doc_builder(my_template, {}, self.cfg)
        self.assertIsInstance(doc_builder["node"].id_dao, DocIdDao)

    def _template(self, template_string):
        return StringIO.StringIO(template_string)


if __name__ == "__main__":
    unittest.main()
