# -*- coding: utf-8 -*-

import pyesdoc.ontologies.cim.v1 as cim

from element import Element


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class Deployment(Element):

    def __init__(self, dao, id_dao, attribute):
        super(Deployment, self).__init__(dao, id_dao, attribute)

    def metadata(self, constraint):
        pass

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.Deployment)
        return element

    def add_to_doc(self, doc, model_element):
        doc.deployments.append(model_element)
        return


class Model(Element):
    # Strictly speaking, model and sub-model are the same elements in
    # the CIM (they are both ModelComponents), but typically they
    # contain different metadata in documents, so I've split them up.

    def __init__(self, dao, id_dao, attribute):
        super(Model, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.ModelComponent)
        required = ["short_name"]
        optional = ["long_name", "description", "release_date"]
        self.populate_attr(element, metadata, required, optional)
        self.id_name = element.short_name
        self.id_dao.add_id("ModelComponent", self.id_name, element.meta.id)
        element.meta.type = unicode(element.meta.type)
        element.types.append(element.meta.type)
        return element

    def add_to_doc(self, doc, model_element):
        # Top-level element, so we don't add it to other docs.
        pass


class SubModel(Element):
    """ Represents a single ModelCompuonent at a lower level in the
    doc hierarchy than the top-level model. For example, a SubModel
    could represent "Atmosphere" or "Aerosols".
    """

    def __init__(self, dao, id_dao, attribute):
        super(SubModel, self).__init__(dao, id_dao, attribute)
        self.container_id_name = ""
        self.model = ""

    def container_metadata(self, container):
        self.dao.container_metadata(container.dao)
        self.container_id_name = container.id_name
        return

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.ModelComponent)
        required = ["short_name", "type"]
        optional = ["long_name", "description"]
        self.populate_attr(element, metadata, required, optional)
        if not self.container_id_name:
            self.container_id_name = self.model
        self.id_name = "%s:%s" % (self.container_id_name, element.short_name)
        self.id_dao.add_id("ModelComponent", self.id_name, element.meta.id)
        element.meta.type = unicode(element.type)
        element.types.append(element.meta.type)
        return element

    def add_to_doc(self, doc, model_element):
        doc.sub_components.append(model_element)
        return


class ComponentProperty(Element):

    def __init__(self, dao, id_dao, attribute):
        super(ComponentProperty, self).__init__(dao, id_dao, attribute)

    def container_metadata(self, container):
        self.dao.container_metadata(container.dao)
        return

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.ComponentProperty)
        required = ["short_name"]
        optional = ["description", "units", "values"]
        self.populate_attr(element, metadata, required, optional)
        element.is_represented = True
        return element

    def add_to_doc(self, doc, model_element):
        doc.properties.append(model_element)
        return
