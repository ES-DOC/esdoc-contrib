# -*- coding: utf-8 -*-

import pyesdoc.ontologies.cim.v1 as cim

from element import Element


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class DataObject(Element):

    def __init__(self, dao, id_dao, attribute):
        super(DataObject, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.DataObject)
        required = ["acronym"]
        optional = ["description"]
        self.populate_attr(element, metadata, required, optional)
        self.id_name = element.acronym
        self.id_dao.add_id("DataObject", self.id_name, element.meta.id)
        return element

    def add_to_doc(self, doc, model_element):
        doc.data.append(model_element)
        return
