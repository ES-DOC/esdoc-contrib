import pyesdoc.ontologies.cim.v1 as cim

from element import Element


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class DocumentSet(Element):

    def __init__(self, dao, id_dao, attribute):
        super(DocumentSet, self).__init__(dao, id_dao, attribute)

    def cim_element(self, metadata, leaves):
        element = self.create_element(cim.DocumentSet)
        self.id_name = metadata["short_name"]
        self.id_dao.add_id("DocumentSet", self.id_name, element.meta.id)
        return element

    def add_to_doc(self, doc, model_element):
        # Top-level element can't be added to another doc.
        pass
