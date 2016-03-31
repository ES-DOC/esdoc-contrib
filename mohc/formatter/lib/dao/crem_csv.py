# -*- coding: utf-8 -*-

""" Data access objects to pull metadata in from CSV files. """

import copy
import csv
from datetime import datetime
import HTMLParser
import os.path
import re

from dao_exception import DaoConnectionException, DaoMetadataException


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>


class CsvDao(object):
    """ Parent class for handling access to the csv dumps of the CREM
    database. Child classes handle element-specific queries and
    processing.
    """

    def __init__(self, connect_env):
        self.connect_env = connect_env
        self.db_dir = ""

    def connect(self, table):
        self.table = table
        csv_path = os.path.join(self.db_dir, self.table)
        try:
            self.csv_file = open(csv_path)
            reader = csv.reader(self.csv_file)
        except IOError as e:
            raise DaoConnectionException(
                "Couldn't connect to %s: %s" % (table, e))
        return reader

    def disconnect(self):
        self.csv_file.close()
        return

    def single_row_query(self, retrieve, table, constraint):
        reader = self.connect(table)
        header = reader.next()
        self._cross_check(header, retrieve, constraint)
        result = {}
        for row in reader:
            record = dict(zip(header, row))
            matched_all = True
            for key in constraint:
                if record[key] != constraint[key]:
                    matched_all = False
                    break
            if matched_all:
                for key in retrieve:
                    result[key] = record[key]
                result = self.clean(result)
                break
        self.disconnect()
        return result

    def multi_row_query(self, retrieve, table, constraint):
        reader = self.connect(table)
        header = reader.next()
        self._cross_check(header, retrieve, constraint)
        clean = []
        for row in reader:
            record = dict(zip(header, row))
            matched_all = True
            for key in constraint:
                if record[key] != constraint[key]:
                    matched_all = False
                    break
            if matched_all:
                result = {}
                for key in retrieve:
                    result[key] = record[key]
                clean.append(self.clean(result))
        return clean

    def rename_keys(self, record, rename):
        for key in rename:
            try:
                record[rename[key]] = record.pop(key)
            except KeyError:
                raise DaoMetadataException(
                    "No attribute called %s in result" % key)
        return record

    def clean(self, metadata):
        for attribute in metadata:
            if metadata[attribute] == "":
                metadata[attribute] = None
            if self._needs_cleaning(metadata[attribute]):
                metadata[attribute] = self.clean_string(metadata[attribute])
        return metadata

    def clean_string(self, to_clean):
        """ Clean up special characters and multiple blank lines in
        our long strings. We can have Windows line feeds (which we
        translate to Linux newlines), multiple blank lines that we
        want to squash down to just one blank line, HTML character
        entities and Unicode chars that are currently giving Mark G
        and I difficulties.
        """
        clean = re.sub(r"(\r\n)", "\n", to_clean)   # Windows newlines
        clean = re.sub(r"(\n){3,}", "\n\n", clean)  # squash blank lines

        # Attempt to convert HTML character entities to characters.
        # This uses an undocumented function in HTMLParser, which
        # StackOverflow says might not work for all possible entities.
        html_parser = HTMLParser.HTMLParser()
        clean = html_parser.unescape(clean)

        #  Until Mark G. and I have decided what to do about Unicode
        #  characters like the degree symbol, strip out anything too
        #  big for ASCII so that I can pass str strings into pyesdoc.
        clean = "".join(i for i in clean if ord(i) < 127)
        return unicode(clean)

    def name_for_expt(self, expt_id):
        """ Returns the short name for the specified expt. """
        record = self.single_row_query(
            ["shortname"], "tblexperiment.csv",
            {"idexperiment": expt_id})
        return record["shortname"]

    def id_for_model(self, model_name):
        """ Finds model id for specified model name. """
        record = self.single_row_query(
            ["idtblmodel"], "tblmodel.csv", {"shortname": model_name})
        if len(record) == 0:
            raise DaoMetadataException(
                "No model matching %s found" % model_name)
        return record["idtblmodel"]

    def id_for_experiment(self, experiment, project_id, model):
        """ Finds experiment id for experiment in specified project. """
        records = self.multi_row_query(
            ["idexperiment", "name"], "tblexperiment.csv",
            {"activityid": project_id, "shortname": experiment})
        if len(records) == 0:
            raise DaoMetadataException(
                "No experiment matching %s found" % experiment)
        # Filter by model name.
        models = set([])
        id = None
        for record in records:
            if re.search(model, record["name"]):
                models.add(record["name"])
                id = record["idexperiment"]
        if len(models) > 1:
            raise DaoMetadataException("Multiple models for %s" % experiment) 
        if not id:
            raise DaoMetadataException("No matching experiment found")
        return id

    def id_for_project(self, project):
        record = self.single_row_query(
            ["idtblactivity"], "tblactivity.csv", {"shortname": project})
        if len(record) == 0:
            raise DaoMetadataException(
                "No project matching %s found" % project)
        return record["idtblactivity"]

    def calendar_for_expt_id(self, expt_id):
        simulation_ids = self.multi_row_query(
            ["idtblsimulation"], "tblsimulation.csv",
            {"experimentid": expt_id})
        calendars = set()
        for simulation_id in simulation_ids:
            records = self.multi_row_query(
                ["runCalendar"], "tblmodelrun.csv",
                {"simulation": simulation_id["idtblsimulation"]})
            for record in records:
                calendars.add(record["runCalendar"])
                if len(calendars) > 1:
                    raise DaoMetadataException(
                        "Multiple calendar types for simulation id "
                        "%s" % self.experiment_id)
        return list(calendars)[0]

    def _needs_cleaning(self, record):
        return isinstance(record, str) or isinstance(record, unicode)

    def _cross_check(self, header, retrieve, constraint):
        # Checks that the values in retrieve and constraint match
        # with header attributes.
        to_check = set(retrieve + constraint.keys())
        for key in to_check:
            if key not in header:
                raise DaoMetadataException(
                    "No attribute called %s in %s" % (key, self.table))
        return

class ModelDao(CsvDao):

    def __init__(self, connect_env):
        super(ModelDao, self).__init__(connect_env)
        self.model = ""
        self.model_id = ""

    def metadata(self, constraint):
        if not self.model:
            raise DaoMetadataException("No model name supplied to DAO")
        self.model_id = self.id_for_model(self.model)
        self.db_table = DbTable(self.model_id, "model")

        record = self.single_row_query(
            ["shortname", "name", "description", "releaseDate"],
            "tblmodel.csv", {"idtblmodel": self.id()})
        if record["releaseDate"]:
            # We have a date as "yyyy-mm-dd", but we need a datetime.
            released = datetime.strptime(record["releaseDate"], "%Y-%m-%d")
            record["releaseDate"] = datetime.combine(
                released, datetime.min.time())
        self.rename_keys(record, {
            "shortname": "short_name", "name": "long_name",
            "releaseDate": "release_date"})
        return record

    def id(self):
        return self.model_id


class ResponsiblePartyDao(CsvDao):

    def __init__(self, connect_env):
        super(ResponsiblePartyDao, self).__init__(connect_env)
        self.parent_table = None
        self.rp_id = ""

    def daos_for_node(self, constraint):
        if self.parent_table is None:
            raise DaoMetadataException(
                "Missing internal db metadata required "
                "to find responsible party records")

        records = self.multi_row_query(
            ["contactid"], self.parent_table.table(),
            {self.parent_table.name(): self.parent_table.id})

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.rp_id = record["contactid"]
            daos.append(dao)
        return daos

    def container_metadata(self, container_dao):
        self.parent_table = container_dao.db_table
        return

    def metadata(self, constraint):
        address_attr = ["city", "adminArea", "postcode", "country"]
        record = self.single_row_query(
            ["fullName", "email", "address", "organisation"] + address_attr,
            "tblindividual.csv", {"idperson": self.rp_id})
        record["address"] = self._address(record)
        for clean_up in address_attr:
            del record[clean_up]
        org_record = self._organisation(record["organisation"])
        del record["organisation"]
        record.update(org_record)
        self.rename_keys(record, {"fullName": "individual_name"})
        return record

    def _address(self, record):
        return ",".join(
            [record["address"], record["city"], record["adminArea"],
            record["postcode"], record["country"]])

    def _organisation(self, org_id):
        record = self.single_row_query(
            ["name", "weblink"], "tblorganisation.csv",
            {"idorganisation": org_id})
        self.rename_keys(
            record, {"name": "organisation_name", "weblink": "url"})
        return record


class CitationDao(CsvDao):

    def __init__(self, connect_env):
        super(CitationDao, self).__init__(connect_env)
        self.parent_table = ""
        self.cite_id = ""

    def daos_for_node(self, constraint):
        if not self.parent_table:
            raise DaoMetadataException(
                "Missing internal db metadata required "
                "to find citation records")

        records = self.multi_row_query(
            ["referenceID"], "tblreferencelist.csv", {
                "objectType": self.parent_table.cite_type(),
                "objectID": self.parent_table.id})

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.cite_id = record["referenceID"]
            daos.append(dao)
        return daos

    def container_metadata(self, container_dao):
        self.parent_table = container_dao.db_table
        return

    def metadata(self, constraint):
        metadata = self.single_row_query(
            ["citation", "date", "fullReference", "weblink"],
            "tblreference.csv", {"idtblCitation": self.cite_id})
        if len(metadata) == 0:
            raise DaoMetadataException(
                "No citation found with cite id %s" % self.cite_id)
        title_end = metadata["citation"].find(")")
        metadata["title"] = metadata["citation"][:title_end+1]
        del metadata["citation"]
        metadata["date"] = datetime(int(metadata["date"]), 1, 1, 0, 0)
        self.rename_keys(
            metadata, {"fullReference": "collective_title",
            "weblink": "location"})
        return metadata


class ComponentPropertyDao(CsvDao):

    def __init__(self, connect_env):
        super(ComponentPropertyDao, self).__init__(connect_env)
        self.comp_id = ""
        self.prop_id = ""

    def daos_for_node(self, constraint):
        if not self.comp_id:
            raise DaoMetadataException("Need component id to find properties")

        records = self.multi_row_query(
            ["idattribute", "value"], "tblattribute.csv",
            {"componentid": self.comp_id})
        daos = []
        for record in records:
            if record["value"]:
                dao = copy.copy(self)
                dao.prop_id = record["idattribute"]
                daos.append(dao)
        return daos

    def container_metadata(self, container_dao):
        self.comp_id = container_dao.comp_id
        return

    def metadata(self, constraint):
        if not self.prop_id:
            raise DaoMetadataException(
                "Need property id to find property metadata")

        metadata = self.single_row_query(
            ["name", "definition", "units", "value"],
            "tblattribute.csv", {"idattribute": self.prop_id})

        metadata["short_name"] = metadata["name"].split(":")[-1]
        del metadata["name"]
        values = []
        for val in metadata["value"].split(","):
            values.append(val.strip())
        metadata["values"] = values
        del metadata["value"]

        self.rename_keys(metadata, {"definition": "description"})
        return metadata


class ModelComponentRefDao(CsvDao):

    def __init__(self, connect_env):
        super(ModelComponentRefDao, self).__init__(connect_env)
        self.project = ""
        self.project_id = ""
        self.experiment = ""
        self.model = ""
        self.expt_id = ""

    def container_metadata(self, container_dao):
        pass

    def daos_for_node(self, constraint):
        if not self.project or not self.experiment or not self.model:
            raise DaoMetadataException("I need project, experiment and model")

        self.project_id = self.id_for_project(self.project)
        self.expt_id = self.id_for_experiment(
            self.experiment, self.project_id, self.model)
        self.model_id = self.id_for_model(self.model)

        return [self]

    def metadata(self, constraint):
        record = self.single_row_query(
            ["shortname"], "tblmodel.csv", {"idtblmodel": self.model_id})
        record["type"] = "ModelComponent"
        self.rename_keys(record, {"shortname": "name"})
        return record


class SubModelDao(CsvDao):

    def __init__(self, connect_env):
        super(SubModelDao, self).__init__(connect_env)
        self.parent_table = None
        self.model = ""
        self.submodel = ""
        self.model_id = ""
        self.comp_id = ""
        self.level = "1"

    def daos_for_node(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        if self.parent_table is None:
            raise DaoMetadataException(
                "Missing internal db metadata required "
                "to find sub-model records")

        # If run with a sub-model as the top level, self.model_id will
        # be set to the id for the supplied model name, but the id in
        # constraint will be the top sub-model's id. For example, if
        # the user has asked to build the "Atmosphere" usb-model for
        # "HadGEM2-ES", model_id will be the id for HadGEM2-ES, but
        # constraint["id"] will be the id for Atmosphere. We want the
        # HadGEM2-ES id.
        if self.model_id:
            query_id = self.model_id
        else:
            query_id = constraint["id"]
        if self.parent_table.node_type == "model":
            parent = "NULL"
        else:
            parent = self.parent_table.id

        records = self.multi_row_query(
            ["idtModelComponent"], "tblmodelcomponent.csv", {
                "parentComponentID": parent, "modelID": query_id,
                "level": self.level})

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.comp_id = record["idtModelComponent"]
            daos.append(dao)
        return daos

    def container_metadata(self, container_dao):
        self.parent_table = container_dao.db_table
        self.model_id = container_dao.model_id
        try:
            self.level = str(int(container_dao.level) + 1)
        except AttributeError:
            # We'll get here if our container is a top-level model or sim.
            self.level = "1"
        return

    def metadata(self, constraint):
        if not self.comp_id:
            # We are trying to get metadata for a sub-model as a top
            # node, so we need to do some extra queries to get
            # required ids.
            self._ids_from_names()

        self.db_table = DbTable(self.comp_id, "component")

        record = self.single_row_query(
            ["name", "description", "type"], "tblmodelcomponent.csv",
            {"idtModelComponent": self.comp_id})
        record["long_name"] = record["name"]
        self.rename_keys(record, {"name": "short_name"})
        return record

    def id(self):
        return self.comp_id

    def _ids_from_names(self):
        if not self.model or not self.submodel:
            raise DaoMetadataException(
                "Need model and submodel name to find metadata")

        self.model_id = self.id_for_model(self.model)
        self.parent_table = DbTable(self.model_id, "model")

        record = self.single_row_query(
            ["idtModelComponent", "level"], "tblmodelcomponent.csv",
            {"modelID": self.model_id, "name": self.submodel})
        if len(record) == 0:
            raise DaoMetadataException(
                "No submodel called %s found in model %s" % (
                self.model, self.submodel))
        self.comp_id = record["idtModelComponent"]
        self.level = record["level"]
        return


class DocumentSetDao(CsvDao):

    def __init__(self, connect_env):
        super(DocumentSetDao, self).__init__(connect_env)
        self.experiment = ""
        self.experiment_id = ""
        self.project = ""
        self.project_id = ""

    def container_metadata(self, container_dao):
        pass

    def metadata(self, constraint):
        if not self.experiment or not self.project:
            raise DaoMetadataException("I need an experiment and a project")
        self.project_id = self.id_for_project(self.project)
        self.experiment_id = self.id_for_experiment(
            self.experiment, self.project_id, self.model)
        return {"short_name": self.experiment}

    def id(self):
        return self.experiment_id


class NumericalExperimentDao(CsvDao):

    def __init__(self, connect_env):
        super(NumericalExperimentDao, self).__init__(connect_env)
        self.experiment = ""
        self.project = ""
        self.model = ""

    def container_metadata(self, container_dao):
        pass

    def metadata(self, constraint):
        if not self.experiment or not self.project or not self.model:
            raise DaoMetadataException(
                "I need a project, experiment and model name")

        self.project_id = self.id_for_project(self.project)
        self.experiment_id = self.id_for_experiment(
            self.experiment, self.project_id, self.model)
        self.db_table = DbTable(self.experiment_id, "experiment")

        record = self.single_row_query(
            ["shortname", "name", "description"], "tblexperiment.csv",
            {"idexperiment": self.experiment_id})
        self.rename_keys(
            record, {"shortname": "short_name", "name": "long_name"})
        self.expt_name = record["short_name"]
        record["calendar"] = self.calendar_for_expt_id(self.experiment_id)
        return record

    def id(self):
        return self.experiment_id


class NumericalRequirementDao(CsvDao):

    def __init__(self, connect_env):
        super(NumericalRequirementDao, self).__init__(connect_env)
        self.parent_expt_name = ""
        self.id = ""

    def container_metadata(self, container_dao):
        self.parent_expt_name = container_dao.expt_name
        return

    def daos_for_node(self, constraint):
        if not self.parent_expt_name:
            raise DaoMetadataException(
                "Need a parent experiment name to find "
                "numerical requirements")
        records = self.multi_row_query(
            ["id", "includes"], "tblrequirements.csv", {})
        daos = []
        for record in records:
            if re.search(self.parent_expt_name, record["includes"]):
                dao = copy.copy(self)
                dao.id = record["id"]
                daos.append(dao)
        return daos

    def metadata(self, constraint):
        record = self.single_row_query(
            ["type", "name", "description"], "tblrequirements.csv",
            {"id": self.id})
        record["type"] = self._translate_type(record["type"])
        return record

    def _translate_type(self, type):
        # Our database types for numerical requirements don't match up
        # neatly with CIM types, so we translate them for consistency.
        crem_to_cim = {
            "initial": "initial", "spatiotemp": "spatiotemporal",
            "forcing": "boundary", "ensemble": "initial"}
        return crem_to_cim[type]


class NumericalRequirementRefDao(CsvDao):

    def __init__(self, connect_env):
        super(NumericalRequirementRefDao, self).__init__(connect_env)
        self.reqt_id = ""
        self.conf_id = ""

    def container_metadata(self, container_dao):
        self.conf_id = container_dao.conf_id

    def daos_for_node(self, constraint):
        records = self.multi_row_query(
            ["requirementid"], "tblconformance.csv", {"id": self.conf_id})
        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.reqt_id = record["requirementid"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        record = self.single_row_query(
            ["name", "description", "type"], "tblrequirements.csv",
            {"id": self.reqt_id})
        cim_type = {
            "initial": "InitialCondition",
            "spatiotemp": "SpatioTemporalConstraint",
            "forcing": "BoundaryCondition",
            "ensemble": "InitialCondition"}
        record["type"] = cim_type[record["type"]]
        return record


class DataObjectDao(CsvDao):

    def __init__(self, connect_env):
        super(DataObjectDao, self).__init__(connect_env)
        self.id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        records = self.multi_row_query(
            ["ancillaryid"], "tblconformancill.csv",
            {"experimentid": constraint["id"]})
        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.id = record["ancillaryid"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        record = self.single_row_query(
            ["shortname", "description"], "tblancillary.csv",
            {"id": self.id})
        record = self.rename_keys(record, {"shortname": "acronym"})
        return record


class PlatformDao(CsvDao):

    def __init__(self, connect_env):
        super(PlatformDao, self).__init__(connect_env)

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        return

    def metadata(self, constraint):
        return {"short_name": "Not provided",
                "long_name": "Not provided",
                "machine_name": "Not provided",
                "compiler_name": "Not provided",
                "compiler_version": "Not provided"}


class SimulationRunDao(CsvDao):

    def __init__(self, connect_env):
        super(SimulationRunDao, self).__init__(connect_env)
        self.experiment_id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        return [self]

    def metadata(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        self.experiment_id = constraint["id"]
        self.db_table = DbTable(self.experiment_id, "simulation")

        # SimulationRun metadata is spread between multiple CREM
        # tables. We get the simulation short and long names from the
        # experiment table, the start/end dates from the simulation
        # table and the calendar from the modelrun table.
        record = self.single_row_query(
            ["shortname", "name"], "tblexperiment.csv",
            {"idexperiment": self.experiment_id})
        record = self.rename_keys(
            record, {"shortname": "short_name", "name": "long_name"})
        record["start_date"], record["end_date"] = self._ensemble_date_range()
        record["calendar"] = self.calendar_for_expt_id(self.experiment_id)
        return record

    def name_for_reference(self, constraint):
        try:
            if constraint["type"] != "NumericalExperiment":
                raise DaoMetadataException(
                    "Invalid type %s" % constraint["type"])
        except KeyError:
            raise DaoMetadataException("I need a type")
        if not self.experiment_id:
            raise DaoMetadataException("I need internal metadata to be set")
        return [self.name_for_expt(self.experiment_id)]

    def _ensemble_date_range(self):
        simulations = self.multi_row_query(
            ["simulationStartDate", "simulationEndDate"],
            "tblsimulation.csv", {"experimentid": self.experiment_id})
        start_date = self._make_dt(simulations[0]["simulationStartDate"])
        end_date = self._make_dt(simulations[0]["simulationEndDate"])
        # We assume ensemble members share the same start date, and
        # we take the latest end date in the ensemble to be the
        # overall end date.
        for simulation in simulations[1:]:
            my_start_date = self._make_dt(simulation["simulationStartDate"])
            my_end_date = self._make_dt(simulation["simulationEndDate"])
            if my_start_date != start_date:
                continue
            if my_end_date > end_date:
                end_date = my_end_date
        return start_date, end_date

    def _make_dt(self, datestamp):
        return datetime.strptime(datestamp, "%Y-%m-%d %H:%M:%S")


class EnsembleDao(CsvDao):

    def __init__(self, connect_env):
        super(EnsembleDao, self).__init__(connect_env)
        self.expt_id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        return [self]

    def metadata(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        self.expt_id = constraint["id"]
        record = self.single_row_query(
            ["shortname", "name", "ensembleType"], "tblexperiment.csv",
            {"idexperiment": constraint["id"]})
        record = self.rename_keys(
            record, {
                "shortname": "short_name", "name": "long_name",
                "ensembleType": "type"})

        type_record = self.single_row_query(
            ["codeDesc"], "tblcodelist.csv",
            {"type": "ensembletype", "code": record["type"]})
        record["type"] = type_record["codeDesc"]
        return record

    def name_for_reference(self, constraint):
        try:
            if constraint["type"] != "NumericalExperiment":
                raise DaoMetadataException(
                    "Invalid type '%s'" % constraint["type"])
        except KeyError:
            raise DaoMetadataException("I need a type")
        if not self.expt_id:
            raise DaoMetadataException("I need internal metadata to be set")
        return [self.name_for_expt(self.expt_id)]


class EnsembleMemberDao(CsvDao):

    def __init__(self, connect_env):
        super(EnsembleMemberDao, self).__init__(connect_env)
        self.sim_id = ""
        self.expt_id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        records = self.multi_row_query(
            ["idtblsimulation", "simulationStartDate"], "tblsimulation.csv",
            {"experimentid": constraint["id"]})
        start_date = records[0]["simulationStartDate"]
        daos = []
        for record in records:
            if record["simulationStartDate"] != start_date:
                continue
            dao = copy.copy(self)
            dao.sim_id = record["idtblsimulation"]
            dao.expt_id = constraint["id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        if not self.sim_id:
            raise DaoMetadataException("I need a constraint on id")
        record = self.single_row_query(
            ["ensembleInit", "ensembleInitType", "ensemblePerturb",
                "shortname", "name"],
            "tblsimulation.csv", {"idtblsimulation": self.sim_id})
        record = self.rename_keys(
            record, {"shortname": "short_name", "name": "long_name"})
        standard_name = "r%si%sp%s" % (
            record["ensembleInit"],
            record["ensembleInitType"],
            record["ensemblePerturb"])
        metadata = {
            "standard_name": standard_name,
            "short_name": record["short_name"],
            "long_name": record["long_name"],
            "description": "Not provided by CREM"}
        return metadata

    def name_for_reference(self, constraint):
        try:
            if constraint["type"] != "SimulationRun":
                raise DaoMetadataException(
                    "Invalid type '%s'" % constraint["type"])
        except KeyError:
            raise DaoMetadataException("I need a type")
        if not self.expt_id:
            raise DaoMetadataException("I need internal metadata to be set")
        return [self.name_for_expt(self.expt_id)]


class ConformanceDao(CsvDao):

    def __init__(self, connect_env):
        super(ConformanceDao, self).__init__(connect_env)
        self.conf_id = ""
        self.expt_id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        # We have two types of conformance - one that requires a data
        # source, and one that doesn't. One table knows about the data
        # source type, and the other knows about all the conformances,
        # so we have to do some filtering to get one sub-set.

        # Find the "data source" types of conformance.
        records = self.multi_row_query(
            ["conformanceid"], "tblconformancill.csv",
            {"experimentid": constraint["id"]})
        source_id = set(rec["conformanceid"] for rec in records)

        if self._data_source():
            ids = source_id
        else:
            # We need to find all the conformance ids for this case
            # and filter out the data source ones.
            records = self.multi_row_query(
                ["id"], "tblconformance.csv",
                {"experimentid": constraint["id"]})
            all_id = set(rec["id"] for rec in records)
            ids = all_id - source_id

        # Collect requirement ids.
        records = []
        for id in ids:
            record = self.single_row_query(
                ["requirementid"], "tblconformance.csv", {"id": id})
            records.append(
                {"conf_id": id, "reqt_id": record["requirementid"]})

        # Finally, we can built the list of DAOs.
        daos = []
        for record in records:
            dao = copy.copy(self)
            for id in ["conf_id", "reqt_id"]:
                setattr(dao, id, record[id])
            dao.expt_id = constraint["id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        if not self.conf_id:
            raise DaoMetadataException("I need a conformance id")
        record = self.single_row_query(
            ["noncompliance", "method", "compliance"],
            "tblconformance.csv", {"id": self.conf_id})
        record = self.rename_keys(
            record, {"method": "type", "compliance": "description"})
        record["is_conformant"] = not record["noncompliance"]
        del record["noncompliance"]
        if not record["description"]:
            record["description"] = "conformance id %s" % self.conf_id
        return record

    def name_for_reference(self, constraint):
        try:
            if constraint["type"] != "DataObject":
                raise DaoMetadataException(
                    "Invalid type %s" % constraint["type"])
        except:
            raise DaoMetadataException("I need a type")
        if not self.conf_id or not self.expt_id:
            raise DaoMetadataException(
                "I need internal metadata to be set")
        records = self.multi_row_query(
            ["ancillaryid"], "tblconformancill.csv",
            {"conformanceid": self.conf_id, "experimentid": self.expt_id})
        name = []
        query = "SELECT shortname as name FROM tblancillary WHERE id = %s"
        for record in records:
            record = self.single_row_query(
                ["shortname"], "tblancillary.csv",
                {"id": record["ancillaryid"]})
            name.append(record["shortname"])
        return name

    def _data_source(self):
        if "type" in self.connect_env:
            if self.connect_env["type"] == "data_source":
                return True
            else:
                raise DaoMetadataException(
                    "Unknown conformance type %s" % connect_env["type"])
        else:
            return False


class GridSpecDao(CsvDao):

    def __init__(self, connect_env):
        super(GridSpecDao, self).__init__(connect_env)
        self.grid_id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        return [self]

    def metadata(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        # First we need to find the grid system id for the model used
        # by our experiment.
        records = self.multi_row_query(
            ["modelid"], "tblsimulation.csv",
            {"experimentid": constraint["id"]})
        models = set(rec["modelid"] for rec in records)
        if len(models) > 1:
            raise DaoMetadataException("Multiple model ids for experiment")

        record = self.single_row_query(
            ["gridsystemid"], "tblmodel.csv",
            {"idtblmodel": records[0]["modelid"]})
        self.grid_system_id = record["gridsystemid"]

        record = self.single_row_query(
            ["ShortName", "LongName", "Description"], "tblgridsystem.csv",
            {"idgridsystem": record["gridsystemid"]})
        record = self.rename_keys(
            record, {
                "ShortName": "short_name", "LongName": "long_name",
                "Description": "description"})
        return record


class GridMosaicDao(CsvDao):

    def __init__(self, connect_env):
        super(GridMosaicDao, self).__init__(connect_env)
        self.mosaic_id = ""
        self.grid_sys_id = ""

    def container_metadata(self, container_dao):
        self.grid_sys_id = container_dao.grid_system_id
        return

    def daos_for_node(self, constraint):
        if not self.grid_sys_id:
            raise DaoMetadataException("I need a grid system id")
        records = self.multi_row_query(
            ["idgridset"], "tblgridset.csv",
            {"idgridsystem": self.grid_sys_id})
        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.mosaic_id = record["idgridset"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        if not self.mosaic_id:
            raise DaoMetadataException("I need a grid mosaic id")
        record = self.single_row_query(
            ["ShortName", "LongName", "Description"],
            "tblgridset.csv", {"idgridset": self.mosaic_id})
        record = self.rename_keys(
            record, {
                "ShortName": "short_name", "LongName": "long_name",
                "Description": "description"})
        # All our grids are this type, so we don't record it in CREM.
        record["type"] = "regular_lat_lon"
        return record


class GridTileDao(CsvDao):

    def __init__(self, connect_env):
        super(GridTileDao, self).__init__(connect_env)
        self.grid_id = ""
        self.mosaic_id = ""

    def container_metadata(self, container_dao):
        self.mosaic_id = container_dao.mosaic_id
        return

    def daos_for_node(self, constraint):
        if not self.mosaic_id:
            raise DaoMetadataException("I need a grid mosaic id")
        records = self.multi_row_query(
            ["idgrid"], "tblgrid.csv", {"idgridset": self.mosaic_id})
        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.grid_id = record["idgrid"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        if not self.grid_id:
            raise DaoMetadataException("No grid id supplied to DAO")
        record = self.single_row_query(
            ["ShortName", "LongName", "Description", "isUniform", "isRegular"],
            "tblgrid.csv", {"idgrid": self.grid_id})
        record = self.rename_keys(
            record, {
                "ShortName": "short_name", "LongName": "long_name",
                "Description": "description", "isUniform": "is_uniform",
                "isRegular": "is_regular"})
        # All our grids have this type.
        record["discretization_type"] = "logically_rectangular"
        # Convert to booleans.
        record["is_uniform"] = record["is_uniform"] == "1"
        record["is_regular"] = record["is_regular"] == "1"
        return record


class DeploymentDao(CsvDao):

    def __init__(self, connect_env):
        super(DeploymentDao, self).__init__(connect_env)

    def daos_for_node(self, constraint):
        return [self]

    def name_for_reference(self, constraint):
        return ["Not provided"]


class DbTable(object):

    def __init__(self, id, node_type):
        self.id = id
        self.node_type = node_type

    def name(self):
        id_attr_name = {
            "model": "idtblmodel",
            "component": "idtModelComponent",
            "simulation": "idexperiment"}
        return id_attr_name[self.node_type]

    def table(self):
        table = {
            "model": "tblmodel.csv",
            "component": "tblmodelcomponent.csv",
            "simulation": "tblexperiment.csv"}
        return table[self.node_type]

    def cite_type(self):
        cite = {
            "model": "MODEL", "component": "COMPONENT",
            "simulation": "SIMULATION"}
        return cite[self.node_type]
