import pyesdoc

from dao.dao_exception import DaoContractException


def make_element(test_case):
    """ Standard method to make an element with no leaves. """
    return test_case.element.cim_element(test_case.valid_metadata, [])


def test_cim_element_contract(test_case):
    """ Standard method to test contract enforced. """
    for required in test_case.valid_metadata:
        invalid = dict(test_case.valid_metadata)
        del invalid[required]
        test_case.assertRaises(
            DaoContractException, test_case.element.cim_element, invalid, [])


def make_empty_component(component):
    """ Returns an empty CIM component of specified type. """
    return pyesdoc.create(component, "cmip5", "mohc")


def config():
    """ Returns valid standard attrs for elements. """
    return {"institute": "mohc", "project": "cmip5"}
