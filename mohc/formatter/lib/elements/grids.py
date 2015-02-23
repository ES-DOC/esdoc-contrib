# -*- coding: utf-8 -*-

import uuid

import pyesdoc.ontologies.cim.v1 as cim

from element import Element


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class GridSpec(Element):

    def __init__(self, dao, id_dao, attribute):
        super(GridSpec, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.GridSpec)
        # Note: short_name isn't mandatory according to the CIM, but
        # we need some metadata we can use for a reference name.
        required = ["short_name"]
        optional = ["long_name", "description"]
        self.populate_attr(element, metadata, required, optional)
        self.id_dao.add_id(
            "GridSpec", metadata["short_name"], element.meta.id)
        return element

    def add_to_doc(self, doc, model_element):
        doc.grids.append(model_element)
        return


class GridMosaic(Element):

    def __init__(self, dao, id_dao, attribute):
        super(GridMosaic, self).__init__(dao, id_dao, attribute)
        self.esm_type = str(attribute["esm_type"])

    def container_metadata(self, container):
        self.dao.container_metadata(container.dao)
        return

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.GridMosaic)
        # Note: is_leaf is also required, but we deduce it from
        # our leaf nodes.
        required = ["type"]
        optional = ["short_name", "long_name", "description"]
        self.populate_attr(element, metadata, required, optional)
        element.id = str(uuid.uuid4())
        element.is_leaf = True
        for leaf in leaves:
            try:
                if leaf.is_mosaic():
                    element.is_leaf = False
                    break
            except AttributeError:
                # We're not worried about leaves that don't have an
                # is_mosaic method.
                pass
        return element

    def is_mosaic(self):
        return True

    def add_to_doc(self, doc, model_element):
        # If model_element is a top-level grid mosaic, add it to the
        # appropriate esm_*_grids list in doc. If it is a leaf of a
        # containing grid mosaic we need to add it to the mosaics list.
        try:
            if self.esm_type == "model":
                doc.esm_model_grids.append(model_element)
            else:
                doc.esm_exchange_grids.append(model_element)
        except AttributeError:
            #  We'll get here if we're adding a mosaic to a mosaic.
            doc.mosaics.append(model_element)
        return


class GridTile(Element):

    def __init__(self, dao, id_dao, attribute):
        super(GridTile, self).__init__(dao, id_dao, attribute)

    def container_metadata(self, container):
        self.dao.container_metadata(container.dao)
        return

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.GridTile)
        required = ["discretization_type"]
        optional = [
            "short_name", "long_name", "description",
            "is_uniform", "is_regular"]
        self.populate_attr(element, metadata, required, optional)
        return element

    def add_to_doc(self, doc, model_element):
        doc.tiles.append(model_element)
        return
