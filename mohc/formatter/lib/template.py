# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 see
# <http://www.gnu.org/licenses/>

""" Parses a user-generated document template and returns a tree of
objects that can be used to build the document. Templates should be
plain-text files in JSON format. The general structure is as follows:

{
    NODE_TYPE: {
        "dao": {DAO_TYPE: {}},
        node_attributes and contents
        and so on...
    }
}

You must provide an institute. You can either provide it via a
"[global]" block in your format.cfg file:

[global]
institute: mohc

Or you can include it in your template file at the top level:

{
    "institute": "mohc",
    NODE_TYPE: {
    ... and so on

Each node must have a data access object that will gather and return
the required (and any optional) metadata needed to populate a node of
the specified type. A node may also have a "contents" attribute which
can be a list of nodes or a dictionary containing nodes defined in the
same way. For example, to define a simple model document, which just
contains citations and responsible party:

{
    "Model": {
        "dao": {"ModelDao": {}},
        "contents": {
            "ResponsibleParty": {
                "dao": {"ResponsiblePartyDao": {}}
            },
            "Citation": {
                "dao": {"CitationDao": {}}
            }
        }
    }
}

The nodes (in this case, "Model", "ResponsibleParty" and "Citation")
must have the same names as a class in the lib/elements inheritance
tree and the dao nodes ("ModelDao", "ResponsiblePartyDao",
"CitationDao") must have the same names as classes in the lib/dao
inheritance hierarchy. If necessary, you may provide options to your
dao objects in a dictionary defined in the template. Alternatively, you
can add a "[database]" configuration block to your format.cfg file.

If you want to define a document template that contains internal or
external references, you also need to define an "id_dao" attribute
that points to a class that can search your local document id
database. Reference attributes have a format like this:

"DocReference": {
    "link": {
        "type": "DataObject",
        "name": ""
    },
    "link_to": "sources_references"

The "link" dictionary specifies the type of object you want to refer
to. If the specified object has been defined in your template and you
want to refer to that instance, you can leave the name string empty.
If you want to refer to an element outside your document you can
provide the name of the element. You also need to provide a "link_to"
attribute which specifies which pyesdoc attribute should be used to
store the reference. This is necessary there isn't a one-to-one
mapping between attribute names and reference types.
"""


import importlib
import inspect
import json

import dao
import elements


class TemplateError(Exception):
    """ Exception raised if there is an error with the template
    (either a JSON syntax problem, or a template-specific error).
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


def parse_template(template_stream):
    """ Parses the template and returns the resulting python
    structure.
    """
    try:
        template = json.load(template_stream)
    except ValueError as exc:
        raise TemplateError("Error parsing JSON template: %s" % exc)
    return template


def doc_builder(template, dao_env, cfg):
    """ Returns a tree of objects. Attributes can be picked up from
    your configuration file (such as "institute"), from command-line
    options or provided in the template. The resulting tree of objects
    can be be walked to build up the CIM document.
    """
    working_template = dict(template)
    global_config = _global_env(working_template, cfg)
    top_node = working_template.keys()
    if len(top_node) > 2:
        raise TemplateError("Too many top-level nodes in template")
    # Template can contain an id_dao for accessing or saving doc ids.
    # It is optional unless the template contains links.
    id_dao = _id_dao(working_template)
    # Pull in database configuration.
    if "database" in cfg:
        dao_env.update(cfg["database"])
    # Build the tree.
    tree = _element(working_template, id_dao, global_config, dao_env)
    # Rearrange the tree so referred-to elements appear to the left of
    # or above the elements that refer to them, so that they will have
    # been built and contain an id we can use to code the reference.
    tree["contents"] = _arrange(tree, set([]))
    return tree


def _id_dao(template):
    try:
        id_type = template["id_dao"].keys()[0]
        id_cls = _find_class(dao, id_type)
        id_dao = id_cls()
        del template["id_dao"]
    except KeyError:
        id_dao = dao.id_dao.Null()
    return id_dao


def _element(template, id_dao, global_config, dao_env):
    """ Called recursively to walk down the template, creating
    elements using the supplied attributes.
    """
    working_template = dict(template)
    element_type, element_attribute = _find_element_type(working_template)
    _check_for_required_attr(element_type, element_attribute, global_config)

    # We need some source of metadata - either a DAO, or an id DAO
    # (which can be used to link to another element).
    if "dao" in element_attribute:
        my_dao = _dao(element_attribute["dao"], global_config, dao_env)
    else:
        if not id_dao:
            raise TemplateError("We have a link, but no id_dao")
        my_dao = id_dao

    # Make the element.
    try:
        my_element = element_type(my_dao, id_dao, element_attribute)
    except TypeError as exc:
        raise TemplateError(
            "Problem making element of type %s: %s" % (element_type, exc))

    # Build up a set of elements referred to by me and my children so
    # we can rearrange the tree into a buildable order later.
    refers_to = set([])
    if "link" in element_attribute:
        refers_to.add(element_attribute["link"]["type"])

    # If this element contains children, we need to create them and
    # add them to our contents.
    leaves = []
    below = set([])
    if "contents" in element_attribute:
        for leaf in element_attribute["contents"]:
            # leaf can be a dictionary, or it can be a list of dicts.
            if isinstance(leaf, dict):
                leaf_name = leaf.keys()[0]
                leaf_attr = leaf[leaf_name]
            else:
                leaf_name = leaf
                leaf_attr = element_attribute["contents"][leaf]
            below.add(leaf_name)
            leaf_element = _element(
                {leaf_name: leaf_attr}, id_dao, global_config, dao_env)
            below.update(leaf_element["below"])
            refers_to.update(leaf_element["refers_to"])
            leaves.append(leaf_element)
    return {
        "node": my_element, "contents": leaves,
        "below": below, "refers_to": refers_to}


def _arrange(node, to_my_left):
    """ Rearranges a template so that any referred-to elements are to
    the left of elements that refer to them.

    We walk the tree top down, left to right to do the rearranging.
    """
    sorted_contents = []
    seen_at_my_level = []
    for leaf in node["contents"]:
        if leaf in sorted_contents:
            # This leaf has already been referred to, so we've
            # already inserted it.
            continue
        if len(leaf["refers_to"]) == 0:
            # We don't refer to anything, so we can go ahead and add
            # ourself now.
            _add_leaf(sorted_contents, seen_at_my_level, leaf)
            continue
        # We refer to at least one element. Check to see if the
        # element(s) we refer to will have been made.
        for referred_to in leaf["refers_to"]:
            if referred_to in seen_at_my_level or \
                    referred_to in to_my_left or referred_to in leaf["below"]:
                # referred_to will be made before us, so we can just
                # add current element to the contents list.
                _add_leaf(sorted_contents, seen_at_my_level, leaf)
            else:
                # We need to find referred_to to the right of us
                # in the tree and add it to our left.
                my_idx = node["contents"].index(leaf)
                found = False
                for right_branch in node["contents"][my_idx+1:]:
                    if _branch_contains_node(right_branch, referred_to):
                        _insert_before_leaf(
                            sorted_contents, seen_at_my_level,
                            right_branch, leaf)
                        _add_leaf(sorted_contents, seen_at_my_level, leaf)
                        found = True
                        break
                if not found:
                    # Assume referred_to is an external doc, so our
                    # element doesn't need to be moved. If it is a
                    # template error it will be picked up later when
                    # the document is built.
                    _add_leaf(sorted_contents, seen_at_my_level, leaf)

    # Now walk down through the tree. We need to build up the set of
    # elements to our left as we go along.
    for idx, leaf in enumerate(sorted_contents):
        if idx > 0:
            for to_left in sorted_contents[0:idx]:
                # We have seen the node at the top of the branch, and
                # all the nodes below it.
                to_my_left.update([_element_from_type(to_left["node"])])
                to_my_left.update(to_left["below"])
        leaf["contents"] = _arrange(leaf, to_my_left)
    return sorted_contents


def _branch_contains_node(branch, node_name):
    # Looks for an element of specified name in branch.
    if _element_from_type(branch["node"]) == node_name:
        return True
    if node_name in branch["below"]:
        return True
    return False


def _insert_before_leaf(sorted_contents, seen, to_insert, leaf):
    # Inserts "to_insert" before "leaf" if "leaf" is already
    # in sorted_contents. If not, we append "to_insert".
    if leaf in sorted_contents:
        leaf_idx = sorted_contents.index(leaf)
        sorted_contents.insert(leaf_idx, to_insert)
        _seen_leaf(seen, to_insert)
    else:
        _add_leaf(sorted_contents, seen, to_insert)
    return


def _add_leaf(sorted_contents, seen, leaf):
    #  Adds leaf to list we're building, and also notes that we've
    #  seen it at this level. If a leaf contains multiple refs we
    #  might be called multiple times at this level, so we need to
    #  check to see if we've already added this leaf to
    #  sorted_contents.
    if not leaf in sorted_contents:
        sorted_contents.append(leaf)
    _seen_leaf(seen, leaf)
    return


def _seen_leaf(seen, leaf):
    seen.append(_element_from_type(leaf["node"]))
    return


def _check_for_required_attr(type, attr, global_config):
    # We must have institute and project for all attributes (pyesdoc
    # needs them).
    for required in ["institute", "project"]:
        if required not in attr:
            try:
                attr[required] = global_config[required]
            except KeyError:
                raise TemplateError(
                    "Must provide %s as global or in element" % required)
    # We either need a dao so we can run a query and get the metadata
    # we need to build a CIM element, or we need a link so we can make
    # a document reference.
    if "dao" not in attr and "link" not in attr:
        raise TemplateError(
            "Element %s needs either a dao or a link" % type.__name__)
    if "dao" in attr and "link" in attr:
        raise TemplateError(
            "Element %s has both a dao and a link" % type.__name__)
    return


def _dao(dao_attr, global_env, dao_env):
    # Builds specified dao type and returns it.
    dao_type, dao_attribute = _find_dao_type(global_env, dao_attr)
    my_dao = dao_type(dao_attribute)
    for attr in dao_env:
        setattr(my_dao, attr, dao_env[attr])
    return my_dao


def _find_dao_type(global_env, type_config):
    # Finds a dao type. Uses a different approach to "elements"
    # because people will be providing a site-specific dao package.
    type = type_config.keys()[0]
    dao_mod = importlib.import_module(global_env["daopkg"])
    my_class = _find_class(dao_mod, type)
    return my_class, type_config[type]


def _find_class(pkg, name):
    try:
        my_class = getattr(pkg, name)
    except AttributeError:
        raise TemplateError("%s not found in %s" % (name, pkg.__name__))
    return my_class


def _find_element_type(type_config):
    classes = _known_elements()
    type = type_config.keys()[0]
    if type not in classes:
        raise TemplateError("%s not a defined element type" % type)
    return classes[type], type_config[type]


def _known_elements():
    known = {}
    classes = inspect.getmembers(elements, inspect.isclass)
    for classname, classvalue in classes:
        known[classname] = classvalue
    return known


def _element_from_type(element_type):
    return type(element_type).__name__


def _global_env(template, cfg):
    global_config = {}
    if "global" in cfg:
        for global_attr in cfg["global"]:
            global_config[global_attr] = cfg["global"][global_attr]
    try:
        global_config["institute"] = template["institute"]
        del template["institute"]
    except KeyError:
        pass
    return global_config
