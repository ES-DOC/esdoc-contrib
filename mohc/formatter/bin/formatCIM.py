#!/usr/local/sci/bin/python2.7

# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 see
# <http://www.gnu.org/licenses/>

""" CLI that builds a CIM document from a template and metadata
extracted from some sort of metadata store.

USAGE: formatCIM.py [-c config_dir] -d model|experiment|submodel
    [-e expt_name] -f xml|json|html [-m model_name] -o output_dir
    -p project [-s submodel_name] -t template_file

-c config_dir
    Points to the directory containing your local "format.cfg" file.
    The default location is assumed to be the etc directory of this
    package.

-d model|experiment|submodel
    Specifies the document type you want to produce.

-e expt_name
    Specifies the experiment name or id to use when finding metadata
    and building a document. Valid values for expt_name will depend on
    how your DAOs query your metadata store. For example, a name could
    be a key for a database table, or a CIM short name.

-f xml|json|html
    Specifies the format of the output document.

-m model_name
    Specifies the name or id of the model to extract metadata for.
    Valid values will depend on how your DAOs query your metadata
    store.

-o output_dir
    Location to store the output document.

-p project
    Specifies the project name, which is required to build any
    document.

-s submodel_name
    Specifies the name or id of the sub-model to extract metadata for.
    Valid values will depend on how your DAOs query your metadata
    store. If you're creating a submodel document, you need to specify
    the model name as well as the sub-model name.

-t template_file
    Points to the file containing the template to build the document.
    At the moment the format is documented in lib/template.py. Once it
    has stabilised it will be documented more thoroughly elsewhere.

ASSUMED PYTHON ENVIRONMENT
    You need to run the script using python2.7. You need the following
    in your PYTHONPATH:

    pyesdoc
    requests
    arrow
    feedparser

    To run formatCIM.py you need the lib sub-directory of the
    MetadataFormatter project in your PYTHONPATH. Depending on how
    your metadata sources work, you may also need modules to connect
    to them such as "MySQLDb".


EXAMPLES
    To build a model document in XML format for HadGEM2-ES:

        formatCIM.py -f xml -d model -m HadGEM2-ES -o model.xml \
            -p CMIP5 -t test/functional/model.fmt

    The test/functional sub-directory contains templates for a model
    document ("model.fmt"), an experiment document ("experiment.fmt")
    and a sub-model document ("sub_model.ftm"). Note the sub-model
    template will produce a document that can be sent to people for
    review, but can't be published (because it isn't a valid
    document). It is provided because it should make reviewing
    documents easier for sub-model owners.

NOTES
    Currently the program calls the validate method of pyesdoc to
    check for validation errors and it will report any it finds, but
    it will still save the document out so you can check it, rather
    than exiting as soon as it sees validation problems.
"""

import os
import sys

import pyesdoc

from cli import PyesdocCli
import config
import dao
import elements
import template


def main():
    option = check_usage()
    dao_env = dao_metadata(option)
    cfg = read_config(option)
    doc_builder = parse_template(option["-t"], dao_env, cfg)
    doc = build_doc(doc_builder)
    save_doc(doc, doc_builder["node"], option["-o"], option["-f"])
    return


def check_usage():
    cli = _cli()
    option = cli.check_usage(sys.argv)
    if not cli.is_format_valid(option["-f"]):
        cli.usage_exit()
    _check_doc_option(cli, option)
    return option


def error_exit(msg):
    cli = _cli()
    cli.error_exit(msg)


def dao_metadata(option):
    metadata_opt = {
        "-e": "experiment", "-m": "model", "-p": "project", "-s": "submodel"}
    dao = {}
    for opt in metadata_opt:
        try:
            dao[metadata_opt[opt]] = option[opt]
        except KeyError:
            pass
    return dao


def read_config(option):
    dir = None
    if "-c" in option:
        dir = option["-c"]
    fc = config.FormatConfig(dir=dir)
    cfg = fc.read_config()
    # Check for mandatory attributes.
    try:
        if "daopkg" not in cfg["global"]:
            error_exit("Missing daopkg in global configuration")
    except KeyError:
        error_exit("Supply a global configuration block")
    # Add global attributes that vary too often to put into a config
    # file.
    cfg["global"]["project"] = option["-p"]
    return cfg


def parse_template(template_file, dao_env, cfg):
    try:
        t = open(template_file)
    except IOError:
        error_exit("Can't open template file %s" % template_file)
    return _doc_builder(t, dao_env, cfg)


def build_doc(doc_builder):
    """ Build a pyesdoc structure representing a CIM document, using
    the tree of objects in doc_builder to drive the production of the
    structure.

    We start building the pyesdoc structure using the top-level node
    in the doc_builder tree. Then we walk down the tree building the
    structure for each node (and its leaf nodes) and adding them to
    the top-level structure as we go.
    """

    top_level = doc_builder["node"]
    doc = top_level.make_doc_from_metadata({}, [])
    constraint = {"id": top_level.id()}

    for node in doc_builder["contents"]:
        node["node"].container_metadata(top_level)
        if _is_leaf(node):
            node["node"].add_to_doc_from_metadata(constraint, doc)
        else:
            _build_container(constraint, doc, node)
    return doc


def save_doc(doc, top_node, output_path, output_format):
    encoding = _cli().encoding(output_format)
    invalid = pyesdoc.validate(doc)
    try:
        path = pyesdoc.write(doc, output_path, encoding)
        print "File written to %s" % path
        os.chmod(path, 0644)
    except Exception as e:
        error_exit("save_file raised an error: %s" % e)
    if len(invalid) != 0:
        error_exit(
            "Document didn't pass validation checks. "
            "Invalid nodes %s" % invalid)
    return


def _cli():
    usage = (
        "[-c config_dir] -d model|experiment|submodel "
        "[-e expt_name] -f xml|json|html [-m model_name] -o output_dir "
        "-p project [-s submodel_name] -t template_file")
    cli = PyesdocCli(
        "c:d:e:f:m:o:p:s:t:", ["-d", "-f", "-o", "-p", "-t"], usage)
    return cli


def _check_doc_option(cli, option):
    extra = {
        "model": ["-m"], "experiment": ["-e", "-m"],
        "submodel": ["-m", "-s"]}
    try:
        for required_extra in extra[option["-d"]]:
            if required_extra not in option:
                error_exit("Require option %s to make %s doc" % (
                    required_extra, option["-d"]))
    except KeyError:
        cli.usage_exit()
    return


def _doc_builder(template_stream, dao_env, cfg):
    try:
        parsed_template = template.parse_template(template_stream)
        return template.doc_builder(parsed_template, dao_env, cfg)
    except template.TemplateError as err:
        error_exit(str(err))


def _build_container(constraint, parent_doc, node):
    """ Builds a pyesdoc structure for an element that contains other
    elements, and calls itself recursively to fill in the contents.
    """
    if _is_leaf(node):
        return node["node"].add_to_doc_from_metadata(constraint, parent_doc)
    # If we get to here, node is a container. It may also be a node
    # type that can be expanded out to a list of nodes (such as
    # sub-model), so we need to loop over each instance, make a
    # document for each one and add all the node's contents to it.
    daos = node["node"].daos_for_node(constraint)
    for dao in daos:
        # Make document for current node.
        node["node"].dao = dao
        node_doc = node["node"].make_doc_from_metadata(
            constraint, _leaf_types(node))
        # Add node's contents to the current document.
        for leaf in node["contents"]:
            leaf["node"].container_metadata(node["node"])
            # Leaf may be a container in its own right.
            _build_container(constraint, node_doc, leaf)
        node["node"].add_to_doc(parent_doc, node_doc)
    return


def _is_leaf(node):
    return len(node["contents"]) == 0


def _leaf_types(node):
    #  Metadata for some nodes depends on their contents. For example,
    #  GridMosaic needs attribute is_leaf set to true if it contains
    #  GridTiles, and it is set to false if it contains GridMosaic
    #  children.
    leaf_types = []
    for leaf in node["contents"]:
        leaf_types.append(leaf["node"])
    return leaf_types


if __name__ == "__main__":
    # try:
    main()
    # except Exception as err:
    #     error_exit("exception from main: %s" % err)
