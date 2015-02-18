import copy
from datetime import datetime
import HTMLParser
import re

import MySQLdb

from dao_exception import DaoConnectionException, DaoMetadataException


# Copyright: (C) Crown copyright 2015, the Met Office
# License: GNU General Public License version 3 
# see <http://www.gnu.org/licenses/>

class CremDao(object):
    """ Parent class for handling access to the CREM database. Child
    classes handle element-specific queries and processing.
    """

    def __init__(self, connect_env):
        self.connect_env = connect_env
        self.dbname = ""
        self.host = ""
        self.user = ""

    def connect(self):
        if self.dbname and self.host and self.user:
            try:
                self.db = MySQLdb.connect(
                    host=self.host, user=self.user, db=self.dbname)
            except MySQLdb.Error as e:
                raise DaoConnectionException(e)
        else:
            raise DaoConnectionException(
                "Missing config required to connect to db")
        return

    def disconnect(self):
        self.db.close()
        return

    def single_row_query(self, query, query_param):
        self.connect()
        cursor = self.query(query, query_param)
        record = cursor.fetchone()
        self.disconnect()
        if not record:
            record = {}
        return self.clean(record)

    def multi_row_query(self, query, query_param):
        self.connect()
        cursor = self.query(query, query_param)
        records = cursor.fetchall()
        self.disconnect()
        clean = []
        for record in records:
            clean.append(self.clean(record))
        return clean

    def query(self, query, query_param):
        cursor = self.db.cursor(MySQLdb.cursors.DictCursor)
        # Use prepared statements for safety.
        cursor.execute(query, query_param)
        return cursor

    def clean(self, metadata):
        for attribute in metadata:
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
        return str(clean)

    def name_for_expt(self, expt_id):
        """ Returns the short name for the specified expt. """
        query = "SELECT shortname FROM tblexperiment WHERE idexperiment = %s"
        record = self.single_row_query(query, (expt_id,))
        return record["shortname"]

    def id_for_model(self, model_name):
        """ Finds model id for specified model name. """
        query = "SELECT idtblmodel as id FROM tblmodel WHERE shortname = %s"
        record = self.single_row_query(query, (model_name,))
        if len(record) == 0:
            raise DaoMetadataException(
                "No model matching %s found" % model_name)
        return record["id"]

    def id_for_experiment(self, experiment, project_id, model):
        """ Finds experiment id for experiment in specified project. """
        like = "%" + model + "%"
        query = (
            "SELECT idexperiment as id FROM tblexperiment WHERE "
            "activityid = %s AND shortname = %s AND name LIKE %s")
        record = self.single_row_query(
            query, (project_id, experiment, like))
        if len(record) == 0:
            raise DaoMetadataException(
                "No experiment matching %s found" % experiment)
        return record["id"]

    def id_for_project(self, project):
        query = (
            "SELECT idtblactivity as id FROM tblactivity WHERE "
            "shortname = %s")
        record = self.single_row_query(query, (project, ))
        if len(record) == 0:
            raise DaoMetadataException(
                "No project matching %s found" % project)
        return record["id"]

    def calendar_for_expt_id(self, expt_id):
        query = (
            "SELECT idtblsimulation as sim_id FROM tblsimulation "
            "WHERE experimentid = %s")
        simulation_ids = self.multi_row_query(query, (expt_id, ))
        calendars = set()
        for simulation_id in simulation_ids:
            query = (
                "SELECT DISTINCT(runCalendar) as calendar FROM "
                "tblmodelrun WHERE simulation = %s")
            records = self.multi_row_query(query, (simulation_id["sim_id"], ))
            for record in records:
                calendars.add(record["calendar"])
                if len(calendars) > 1:
                    raise DaoMetadataException(
                        "Multiple calendar types for simulation id "
                        "%s" % self.experiment_id)
        return list(calendars)[0]

    def _needs_cleaning(self, record):
        return isinstance(record, str) or isinstance(record, unicode)


class ModelDao(CremDao):

    def __init__(self, connect_env):
        super(ModelDao, self).__init__(connect_env)
        self.model = ""
        self.model_id = ""

    def metadata(self, constraint):
        if not self.model:
            raise DaoMetadataException("No model name supplied to DAO")

        self.model_id = self.id_for_model(self.model)
        self.db_table = DbTable(self.id(), "model")

        query = (
            "SELECT shortname as short_name, name as long_name, "
            "description, releaseDate as release_date "
            "FROM tblmodel WHERE idtblmodel = %s")
        record = self.single_row_query(query, (self.id(),))
        if record["release_date"]:
            # We have a date, but we need a datetime.
            record["release_date"] = datetime.combine(
                record["release_date"], datetime.min.time())
        return record

    def id(self):
        return self.model_id


class ResponsiblePartyDao(CremDao):

    def __init__(self, connect_env):
        super(ResponsiblePartyDao, self).__init__(connect_env)
        self.parent_table = None
        self.rp_id = ""

    def daos_for_node(self, constraint):
        if self.parent_table is None:
            raise DaoMetadataException(
                "Missing internal db metadata required "
                "to find responsible party records")

        query = "SELECT contactid FROM " + self.parent_table.table()
        query = query + " WHERE " + self.parent_table.name() + " = %s"
        records = self.multi_row_query(query, (self.parent_table.id,))

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
        query = (
            "SELECT a.fullname as individual_name, a.email as email, "
            "{sql} as address, b.name as organisation_name, "
            "b.weblink as url FROM tblindividual as a "
            "JOIN tblorganisation as b "
            "ON a.organisation=b.idorganisation "
            "WHERE idperson=%s")
        query = query.format(sql=self._address("a"))
        record = self.single_row_query(query, (self.rp_id,))
        return record

    def _address(self, table):
        """ SQL to build an address from component parts. """
        query = [
            "concat({table}.address,',',", "{table}.city,',',",
            "{table}.adminArea,',',", "{table}.postcode,',',",
            "{table}.country)"]
        query = "".join(query)
        return query.format(table=table)


class CitationDao(CremDao):

    def __init__(self, connect_env):
        super(CitationDao, self).__init__(connect_env)
        self.parent_table = ""
        self.cite_id = ""

    def daos_for_node(self, constraint):
        if not self.parent_table:
            raise DaoMetadataException(
                "Missing internal db metadata required "
                "to find citation records")

        query = (
            "SELECT referenceID FROM tblreferencelist WHERE "
            "objectType = %s AND objectID = %s")
        records = self.multi_row_query(
            query, (self.parent_table.cite_type(), self.parent_table.id))

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
        query = (
            "SELECT citation, date, fullReference as collective_title, "
            "weblink as location FROM tblreference "
            "WHERE idtblCitation = %s")
        metadata = self.single_row_query(query, (self.cite_id,))

        # Title format isn't quite right, so we need to tweak.
        title_end = metadata["citation"].find(")")
        metadata["title"] = metadata["citation"][:title_end+1]
        del metadata["citation"]

        # We only have a year in CREM, so we will convert to datetime
        # using a default date of 1 Jan 00:00.
        metadata["date"] = datetime(int(metadata["date"]), 1, 1, 0, 0)

        return metadata


class ComponentPropertyDao(CremDao):

    def __init__(self, connect_env):
        super(ComponentPropertyDao, self).__init__(connect_env)
        self.comp_id = ""
        self.prop_id = ""

    def daos_for_node(self, constraint):
        if not self.comp_id:
            raise DaoMetadataException("Need component id to find properties")

        query = (
            "SELECT idAttribute as property_id FROM tblattribute "
            "WHERE componentid = %s AND value != ''")
        records = self.multi_row_query(query, (self.comp_id, ))

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.prop_id = record["property_id"]
            daos.append(dao)
        return daos

    def container_metadata(self, container_dao):
        self.comp_id = container_dao.comp_id
        return

    def metadata(self, constraint):
        if not self.prop_id:
            raise DaoMetadataException(
                "Need property id to find property metadata")

        query = (
            "SELECT SUBSTRING_INDEX(name,':',-1) as short_name, "
            "definition as description, units, value as `values` "
            "FROM tblattribute WHERE idAttribute = %s")
        metadata = self.single_row_query(query, (self.prop_id,))
        values = []
        for val in metadata["values"].split(","):
            values.append(val.strip())
        metadata["values"] = values
        return metadata


class ModelComponentRefDao(CremDao):

    def __init__(self, connect_env):
        super(ModelComponentRefDao, self).__init__(connect_env)
        self.model = ""
        self.project = ""
        self.project_id = ""
        self.experiment = ""
        self.expt_id = ""

    def container_metadata(self, container_dao):
        pass

    def daos_for_node(self, constraint):
        if not self.project or not self.experiment or not self.model:
            raise DaoMetadataException("I need project, experiment and model")

        self.project_id = self.id_for_project(self.project)
        self.expt_id = self.id_for_experiment(
            self.experiment, self.project_id, self.model)

        query = (
            "SELECT DISTINCT(modelid) as id FROM tblsimulation WHERE "
            "activityid = %s AND experimentid = %s")
        records = self.multi_row_query(query, (self.project_id, self.expt_id))
        if len(records) > 1:
            raise DaoMetadataException(
                "Found multiple models in a single experiment")

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.model_id = record["id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        query = (
            "SELECT shortname as name FROM tblmodel WHERE idtblmodel = %s")
        record = self.single_row_query(query, (self.model_id, ))
        record["type"] = "ModelComponent"
        return record


class SubModelDao(CremDao):

    def __init__(self, connect_env):
        super(SubModelDao, self).__init__(connect_env)
        self.parent_table = None
        self.model = ""
        self.submodel = ""
        self.model_id = ""
        self.comp_id = ""
        self.level = 1

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

        query = "SELECT idtModelComponent as compid FROM tblmodelcomponent "
        if self.parent_table.node_type == "model":
            query = query + "WHERE parentComponentID is NULL "
        else:
            query = query + "WHERE parentComponentID='%s' " % \
                self.parent_table.id
        query = query + "AND modelID = %s AND level = %s"
        records = self.multi_row_query(query, (query_id, self.level))

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.comp_id = record["compid"]
            daos.append(dao)
        return daos

    def container_metadata(self, container_dao):
        self.parent_table = container_dao.db_table
        self.model_id = container_dao.model_id
        try:
            self.level = container_dao.level + 1
        except AttributeError:
            # We'll get here if our container is a top-level model or sim.
            self.level = 1
        return

    def metadata(self, constraint):
        if not self.comp_id:
            # We are trying to get metadata for a sub-model as a top
            # node, so we need to do some extra queries to get
            # required ids.
            self._ids_from_names()

        self.db_table = DbTable(self.comp_id, "component")

        query = (
            "SELECT name as short_name, name as long_name, "
            "description, type FROM tblmodelcomponent WHERE "
            "idtModelComponent = %s")
        record = self.single_row_query(query, (self.comp_id, ))
        return record

    def id(self):
        return self.comp_id

    def _ids_from_names(self):
        if not self.model or not self.submodel:
            raise DaoMetadataException(
                "Need model and submodel name to find metadata")

        self.model_id = self.id_for_model(self.model)
        self.parent_table = DbTable(self.model_id, "model")

        query = (
            "SELECT idtModelComponent as comp_id, "
            "level FROM tblmodelcomponent "
            "WHERE modelID = %s AND name = %s")
        record = self.single_row_query(query, (self.model_id, self.submodel))
        if len(record) == 0:
            raise DaoMetadataException(
                "No submodel called %s found in model %s" % (
                self.model, self.submodel))
        self.comp_id = record["comp_id"]
        self.level = record["level"]
        return


class DocumentSetDao(CremDao):

    def __init__(self, connect_env):
        super(DocumentSetDao, self).__init__(connect_env)
        self.experiment = ""
        self.experiment_id = ""
        self.model = ""
        self.project = ""
        self.project_id = ""

    def container_metadata(self, container_dao):
        pass

    def metadata(self, constraint):
        if not self.experiment or not self.project or not self.model:
            raise DaoMetadataException(
                "I need a project, an experiment and a model")
        self.project_id = self.id_for_project(self.project)
        self.experiment_id = self.id_for_experiment(
            self.experiment, self.project_id, self.model)
        return {"short_name": self.experiment}

    def id(self):
        return self.experiment_id


class NumericalExperimentDao(CremDao):

    def __init__(self, connect_env):
        super(NumericalExperimentDao, self).__init__(connect_env)
        self.experiment = ""
        self.model = ""
        self.project = ""

    def container_metadata(self, container_dao):
        pass

    def metadata(self, constraint):
        if not self.experiment or not self.project or not self.model:
            raise DaoMetadataException(
                "I need a project, an experiment and a model name")

        self.project_id = self.id_for_project(self.project)
        self.experiment_id = self.id_for_experiment(
            self.experiment, self.project_id, self.model)
        self.db_table = DbTable(self.experiment_id, "experiment")

        query = (
            "SELECT shortname as short_name, name as long_name, "
            "description FROM tblexperiment WHERE idexperiment = %s")
        record = self.single_row_query(query, (self.experiment_id,))
        self.expt_name = record["short_name"]
        record["calendar"] = self.calendar_for_expt_id(self.experiment_id)
        return record

    def id(self):
        return self.experiment_id


class NumericalRequirementDao(CremDao):

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

        query = "SELECT id from tblrequirements WHERE includes LIKE %s"
        like = "%" + self.parent_expt_name + "%"
        records = self.multi_row_query(query, (like, ))

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.id = record["id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        query = (
            "SELECT type, name, description FROM tblrequirements "
            "WHERE id = %s")
        record = self.single_row_query(query, (self.id, ))
        record["type"] = self._translate_type(record["type"])
        return record

    def _translate_type(self, type):
        # Our database types for numerical requirements don't match up
        # neatly with CIM types, so we translate them for consistency.
        crem_to_cim = {
            "initial": "initial", "spatiotemp": "spatiotemporal",
            "forcing": "boundary", "ensemble": "initial"}
        return crem_to_cim[type]


class NumericalRequirementRefDao(CremDao):

    def __init__(self, connect_env):
        super(NumericalRequirementRefDao, self).__init__(connect_env)
        self.reqt_id = ""
        self.conf_id = ""

    def container_metadata(self, container_dao):
        self.conf_id = container_dao.conf_id

    def daos_for_node(self, constraint):
        query = (
            "SELECT requirementid as id FROM tblconformance WHERE "
            "id = %s")
        records = self.multi_row_query(query, (self.conf_id, ))

        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.reqt_id = record["id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        query = (
            "SELECT name, description, type FROM tblrequirements "
            "WHERE id = %s")
        record = self.single_row_query(query, (self.reqt_id, ))
        cim_type = {
            "initial": "InitialCondition",
            "spatiotemp": "SpatioTemporalConstraint",
            "forcing": "BoundaryCondition",
            "ensemble": "InitialCondition"}
        record["type"] = cim_type[record["type"]]
        return record


class DataObjectDao(CremDao):

    def __init__(self, connect_env):
        super(DataObjectDao, self).__init__(connect_env)
        self.id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        query = (
            "SELECT ancillaryid from tblconformancill WHERE "
            "experimentid = %s")
        records = self.multi_row_query(query, (constraint["id"], ))
        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.id = record["ancillaryid"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        query = (
            "SELECT shortname as acronym, description from tblancillary "
            "WHERE id = %s")
        record = self.single_row_query(query, (self.id, ))
        return record


class PlatformDao(CremDao):

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


class SimulationRunDao(CremDao):

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
        query = (
            "SELECT shortname as short_name, name as long_name FROM "
            "tblexperiment WHERE idexperiment = %s")
        record = self.single_row_query(query, (self.experiment_id,))
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
        query = (
            "SELECT simulationStartDate as start_date, "
            "simulationEndDate as end_date fROM tblsimulation WHERE "
            "experimentid = %s")
        simulations = self.multi_row_query(query, (self.experiment_id,))
        start_date = simulations[0]["start_date"]
        end_date = simulations[0]["end_date"]
        # We assume ensemble members share the same start date, and
        # we take the latest end date in the ensemble to be the
        # overall end date.
        for simulation in simulations[1:]:
            if simulation["start_date"] != start_date:
                continue
            if simulation["end_date"] > end_date:
                end_date = simulation["end_date"]
        return start_date, end_date


class EnsembleDao(CremDao):

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
        query = (
            "SELECT shortname as short_name, name as long_name, "
            "ensembleType as type FROM tblexperiment "
            "WHERE idexperiment = %s")
        record = self.single_row_query(query, (constraint["id"], ))
        query = (
            "SELECT codeDesc FROM tblcodelist WHERE "
            "type = 'ensembletype' and code = %s")
        type_record = self.single_row_query(query, (record["type"], ))
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


class EnsembleMemberDao(CremDao):

    def __init__(self, connect_env):
        super(EnsembleMemberDao, self).__init__(connect_env)
        self.sim_id = ""
        self.expt_id = ""

    def container_metadata(self, container_dao):
        return

    def daos_for_node(self, constraint):
        if "id" not in constraint:
            raise DaoMetadataException("I need a constraint on id")
        query = (
            "SELECT idtblsimulation as sim_id, "
            "simulationStartDate as start_date "
            "from tblsimulation WHERE experimentid = %s")
        records = self.multi_row_query(query, (constraint["id"], ))
        start_date = records[0]["start_date"]
        daos = []
        for record in records:
            if record["start_date"] != start_date:
                continue
            dao = copy.copy(self)
            dao.sim_id = record["sim_id"]
            dao.expt_id = constraint["id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        if not self.sim_id:
            raise DaoMetadataException("I need a constraint on id")
        query = (
            "SELECT ensembleInit, ensembleInitType, ensemblePerturb, "
            "shortname as short_name, name as long_name "
            "FROM tblsimulation WHERE idtblsimulation = %s")
        record = self.single_row_query(query, (self.sim_id, ))
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


class ConformanceDao(CremDao):

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
        query = (
            "SELECT DISTINCT conformanceid as conf_id FROM tblconformancill "
            "WHERE experimentid = %s")
        records = self.multi_row_query(query, (constraint["id"], ))
        source_id = set(rec["conf_id"] for rec in records)

        if self._data_source():
            ids = source_id
        else:
            # We need to find all the conformance ids for this case
            # and filter out the data source ones.
            query = (
                "SELECT id as conf_id FROM tblconformance WHERE "
                "experimentid = %s")
            records = self.multi_row_query(query, (constraint["id"], ))
            all_id = set(rec["conf_id"] for rec in records)
            ids = all_id - source_id

        # Collect requirement ids.
        records = []
        for id in ids:
            query = (
                "SELECT requirementid as reqt_id FROM tblconformance "
                "WHERE id = %s")
            record = self.single_row_query(query, (id, ))
            records.append({"conf_id": id, "reqt_id": record["reqt_id"]})

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
        query = (
            "SELECT noncompliance, method as type, compliance as description "
            "FROM tblconformance WHERE id = %s")
        record = self.single_row_query(query, (self.conf_id, ))
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
        query = (
            "SELECT ancillaryid FROM tblconformancill WHERE "
            "conformanceid = %s AND experimentid = %s")
        records = self.multi_row_query(query, (self.conf_id, self.expt_id))
        name = []
        query = "SELECT shortname as name FROM tblancillary WHERE id = %s"
        for record in records:
            record = self.single_row_query(query, (record["ancillaryid"],))
            name.append(record["name"])
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


class GridSpecDao(CremDao):

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
        query = (
            "SELECT DISTINCT modelid FROM tblsimulation "
            "WHERE experimentid = %s")
        records = self.multi_row_query(query, (constraint["id"],))
        if len(records) > 1:
            raise DaoMetadataException(
                "Multiple model ids for experiment")

        query = "SELECT gridsystemid FROM tblmodel WHERE idtblmodel = %s"
        record = self.single_row_query(query, (records[0]["modelid"], ))
        self.grid_system_id = record["gridsystemid"]

        query = (
            "SELECT ShortName as short_name, "
            "LongName as long_name, Description as description "
            "from tblgridsystem WHERE idgridsystem = %s")
        record = self.single_row_query(query, (record["gridsystemid"], ))
        return record


class GridMosaicDao(CremDao):

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
        query = (
            "SELECT idgridset as mosaic_id FROM tblgridset "
            "WHERE idgridsystem = %s")
        records = self.multi_row_query(query, (self.grid_sys_id, ))
        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.mosaic_id = record["mosaic_id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        if not self.mosaic_id:
            raise DaoMetadataException("I need a grid mosaic id")
        query = (
            "SELECT ShortName as short_name, "
            "LongName as long_name, Description as description "
            "from tblgridset WHERE idgridset = %s")
        record = self.single_row_query(query, (self.mosaic_id, ))
        # All our grids are this type, so we don't record it in CREM.
        record["type"] = "regular_lat_lon"
        return record


class GridTileDao(CremDao):

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
        query = "SELECT idgrid as grid_id FROM tblgrid WHERE idgridset = %s"
        records = self.multi_row_query(query, (self.mosaic_id, ))
        daos = []
        for record in records:
            dao = copy.copy(self)
            dao.grid_id = record["grid_id"]
            daos.append(dao)
        return daos

    def metadata(self, constraint):
        if not self.grid_id:
            raise DaoMetadataException("No grid id supplied to DAO")
        query = (
            "SELECT ShortName as short_name, "
            "LongName as long_name, Description as description, "
            "IsUniform as is_uniform, IsRegular as is_regular "
            "from tblgrid WHERE idgrid = %s")
        record = self.single_row_query(query, (self.grid_id, ))
        # All our grids have this type.
        record["discretization_type"] = "logically_rectangular"
        # Convert to booleans.
        record["is_uniform"] = record["is_uniform"] == 1
        record["is_regular"] = record["is_regular"] == 1
        return record


class DeploymentDao(CremDao):

    def __init__(self, connect_env):
        super(DeploymentDao, self).__init__(connect_env)

    def daos_for_node(self, constraint):
        return [self]

    def name_for_reference(self, constraint):
        return ["Not provided"]


class DbTable(object):
    """ Tiny data class for wrapping up metadata for container types,
    such as their id value, the name of their id attribute, and the
    table that contains their record. Used when a leaf node needs
    access to metadata about its parent node.
    """

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
            "model": "tblmodel", "component": "tblmodelcomponent",
            "simulation": "tblexperiment"}
        return table[self.node_type]

    def cite_type(self):
        cite = {"model": "MODEL", "component": "COMPONENT",
                "simulation": "SIMULATION"}
        return cite[self.node_type]
