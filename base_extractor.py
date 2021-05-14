# -*- coding: utf-8 -*-
""" Base Extractor

This module provies an Abstract Base Class with some utility methods to extract
from cloud databases to "live to hyper" Tableau Datasources.
Database specific Extractor classes extend this to manage queries, exports and
schema discovery via the database vendor supplied client.

"""


from abc import ABC, abstractmethod
import logging
from pathlib import Path
import time

import tableauserverclient as TSC
import tableau_restapi_helpers as REST
from tableauhyperapi import (
    HyperProcess,
    Connection,
    TableDefinition,
    TableName,
    SqlType,
    Telemetry,
    Inserter,
    CreateMode,
    HyperException,
    NOT_NULLABLE,
    NULLABLE,
    escape_name,
    escape_string_literal,
)

logger = logging.getLogger("hyper_samples.extractor.base")

TELEMETRY = Telemetry.SEND_USAGE_DATA_TO_TABLEAU
"""TELEMETRY: Send usage data to Tableau
    Set to Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU to disable
"""

MAX_ROWS_PER_FILE = 100000
"""MAX_ROWS_PER_FILE (int): Split output into smaller files for large query results"""

SAMPLE_ROWS = 1000
"""SAMPLE_ROWS (int): Default number of rows for LIMIT when using load_sample"""

ASYNC_JOB_POLL_INTERVAL = 10
"""ASYNC_JOB_POLL_INTERVAL (int): How many seconds to wait between polls for Asynchronous Job completion"""

DEFAULT_SITE_ID = ""
"""DEFAULT_SITE_ID (string): Default site ID"""

HYPER_CONNECTION_PARAMETERS = {"lc_time": "en_GB", "date_style": "YMD"}
"""HYPER_CONNECTION_PARAMETERS (dict): Options are documented in the Tableau Hyper documentation, chapter “Connection Settings”

- lc_time - Controls the Locale setting that is used for dates. A Locale controls which cultural preferences the application should apply. For example, the literal Januar 1. 2002 can be converted to a date with the German locale de but not with the English locale en_US.
    Default value: en_US
    Allowed values start with a two-letter ISO-639 language code and an optional two-letter ISO-3166 country code. If a country code is used, an underscore has to be used to separate it from the language code. Some examples are: en_US (English: United States), en_GB (English: Great Britain), de (German), de_AT (German: Austria).

- date_style - Controls how date strings are interpreted. Y, M and D stand for Year, Month, and Day respectively.
    Default value: MDY
    Accepted values: MDY, DMY, YMD, YDM
"""


class TableauJobError(Exception):
    """Exception: Tableau Job Failed"""

    pass


class TableauResourceNotFoundError(Exception):
    """Exception: Tableau Resource not found"""

    pass


class HyperSQLTypeMappingError(Exception):
    """Exception: Could not identify a target Hyper field type for source database field"""

    pass


class BaseExtractor(ABC):
    """ Abstract Base Class defining the standard Extractor Interface"""

    def __init__(
        self,
        tableau_username,
        tableau_password,
        tableau_hostname,
        tableau_project,
        tableau_site_id=DEFAULT_SITE_ID,
    ):
        super().__init__()
        self.tableau_site_id = tableau_site_id
        self.tableau_hostname = tableau_hostname
        self.tableau_auth = TSC.TableauAuth(
            username=tableau_username,
            password=tableau_password,
            site_id=tableau_site_id,
        )
        self.tableau_server = TSC.Server(tableau_hostname, use_server_version=True)
        self.tableau_server.auth.sign_in(self.tableau_auth)
        self.tableau_project_name = tableau_project
        self.tableau_project_id = self._get_project_id(tableau_project)

    def _get_project_id(self, tab_project):
        """
        Return project_id for tab_project
        """
        # Get project_id from project_name
        all_projects, pagination_item = self.tableau_server.projects.get()

        for project in all_projects:
            if project.name == tab_project:
                return project.id

        logger.error("No project found for:{}".format(tab_project))
        raise TableauResourceNotFoundError(
            "No project found for:{}".format(tab_project)
        )

    def get_datasource_id(self, tab_datasource):
        """
        Return id for tab_datasource
        """
        # Get project_id from project_name

        all_datasources, pagination_item = self.tableau_server.datasources.get()
        for datasource in all_datasources:
            if datasource.name == tab_datasource:
                return datasource.id

        raise TableauResourceNotFoundError(
            "No datasource found for:{}".format(tab_datasource)
        )

    def wait_for_async_job(self, async_job_id):
        """
        Waits for async job to complete and returns finish_code
        """

        completed_at = None
        finish_code = None
        jobinfo = None
        while completed_at is None:
            jobinfo = self.tableau_server.jobs.get_by_id(async_job_id)
            completed_at = jobinfo.completed_at
            finish_code = jobinfo.finish_code
            logger.info(
                "Job {} ... progress={} finishCode={}".format(
                    async_job_id, jobinfo.progress, finish_code
                )
            )
            time.sleep(ASYNC_JOB_POLL_INTERVAL)

        logger.info("Job {} Completed: {}".format(async_job_id, str(jobinfo)))
        return finish_code

    def query_result_to_hyper_files(self, query_result_iter, target_table_def):
        """
        Writes query output to one or more Hyper files
        Returns a list of output Hyper files

        query_result_iter (obj): Iterator containing result rows
        target_table_def (TableDefinition): Schema for target extract table
        """
        output_hyper_files = []
        # TODO: Split output into smaller files when query result > MAX_ROWS_PER_FILE
        path_to_database = Path("temp.hyper")
        output_hyper_files.append(path_to_database)

        with HyperProcess(telemetry=TELEMETRY) as hyper:

            # Creates new Hyper extract file
            # Replaces file with CreateMode.CREATE_AND_REPLACE if it already exists.
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.CREATE_AND_REPLACE,
            ) as connection:

                connection.catalog.create_schema(
                    schema=target_table_def.table_name.schema_name
                )
                connection.catalog.create_table(table_definition=target_table_def)
                with Inserter(connection, target_table_def) as inserter:
                    inserter.add_rows(query_result_iter())
                    inserter.execute()

                row_count = connection.execute_scalar_query(
                    query=f"SELECT COUNT(*) FROM {target_table_def.table_name}"
                )
                logger.info(
                    f"The number of rows in table {target_table_def.table_name} is {row_count}."
                )

            logger.info("The connection to the Hyper file has been closed.")
        logger.info("The Hyper process has been shut down.")
        return output_hyper_files

    def csv_to_hyper_files(self, path_to_csv, target_table_def):
        """
        Writes csv to one or more Hyper files
        Returns a list of output Hyper files

        path_to_csv (string): CSV file containing result rows
        target_table_def (TableDefinition): Schema for target extract table
        """
        output_hyper_files = []
        # TODO: Split output into smaller files when csv contains > MAX_ROWS_PER_FILE
        path_to_database = Path("temp.hyper")
        output_hyper_files.append(path_to_database)

        with HyperProcess(telemetry=TELEMETRY) as hyper:
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.CREATE_AND_REPLACE,
                parameters=HYPER_CONNECTION_PARAMETERS,
            ) as connection:

                connection.catalog.create_schema(
                    schema=target_table_def.table_name.schema_name
                )
                connection.catalog.create_table(table_definition=target_table_def)

                count_rows = connection.execute_command(
                    command=f"COPY {target_table_def.table_name} from {escape_string_literal(path_to_csv)} "
                    f"with (format csv, NULL 'NULL', delimiter ',', header)"
                )
                logger.info(
                    f"Inserted {count_rows} into table {target_table_def.table_name}"
                )
            logger.debug("The connection to the Hyper file has been closed.")
        logger.debug("The Hyper process has been shut down.")
        return output_hyper_files

    def publish_hyper_file(
        self,
        path_to_database,
        tab_ds_name,
        publish_mode=TSC.Server.PublishMode.CreateNew,
    ):
        """
        Publishes a Hyper file to Tableau Server

        path_to_database (string): Hyper file to publish
        tab_ds_name (string): Target datasource name
        publish_mode: One of TSC.Server.[Overwrite|Append|CreateNew] (default=CreateNew)

        Returns the Datasource ID
        """
        # This is used to create new datasources and to implement the APPEND action
        #
        # Create the datasource object with the project_id
        datasource = TSC.DatasourceItem(self.tableau_project_id, name=tab_ds_name)

        logger.info(f"Publishing {path_to_database} to {tab_ds_name}...")
        # Publish datasource
        datasource = self.tableau_server.datasources.publish(
            datasource, path_to_database, publish_mode
        )
        logger.info("Datasource published. Datasource ID: {0}".format(datasource.id))
        return datasource.id

    def update_datasource_from_hyper_file(
        self,
        path_to_database,
        tab_ds_name,
        match_columns=None,
        match_conditions_json=None,
        changeset_table_name="updated_rows",
        action="UPDATE",
    ):
        """
        Updates a datasource on Tableau Server with a changeset from a hyper file

        path_to_database (string): The hyper file containing the changeset
        tab_ds_name (string): Target Tableau datasource
        match_columns (array of tuples): Array of (source_col, target_col) pairs
        match_conditions_json (string): Define conditions for matching rows in json format.  See Hyper API guide for details.
        changeset_table_name (string): The name of the table in the hyper file that contains the changest (default="updated_rows")
        action (string): One of "UPDATE" or "DELETE" (Default="UPDATE")

        NOTES:
        - match_columns overrides match_conditions_json if both are specified
        - set path_to_database to None if conditional delete
            (e.g. json_request="condition": { "op": "<", "target-col": "col1", "const": {"type": "datetime", "v": "2020-06-00"}})
        - When action is DELETE, it is an error if the source table contains any additional columns not referenced by the condition. Those columns are pointless and we want to let the user know, so they can fix their scripts accordingly.
        """

        match_conditions_args = []
        if match_columns is not None:
            for match_pair in match_columns:
                match_conditions_args.append(
                    {
                        "op": "=",
                        "source-col": match_pair[0],
                        "target-col": match_pair[1],
                    }
                )
            if len(match_conditions_args) > 1:
                match_conditions_json = {"op": "and", "args": match_conditions_args}
            else:
                match_conditions_json = match_conditions_args[0]

        if action == "UPDATE":
            # Update action
            # The Update operation updates existing tuples inside the target table.
            # It uses a `condition` to decide which tuples (rows) to update.
            #
            # Example
            #
            # {"action": "update",
            #  "target-table": "my_data",
            #  "source-table": "uploaded_table",
            #  "condition": {"op": "=", "target-col": "row_id", "source-col": "update_row_id"}
            # }
            # Parameters:
            #
            # `target-table` (string; required): the table name inside the target database into which we will insert data
            # `target-schema` (string; required): the schema name inside the target database; default: the one, unique schema name inside the target database in case the target db has only one schema; error otherwise
            # `source-table` (string; required): the table name inside the source database from which the data will be inserted
            # `source-schema` (string; required): analogous to target-schema, but for the source table
            # `condition` (condition-specification; required): specifies the condition used to select the columns to be updated
            # To determine the updated columns, we will use the following default algorithm:
            #
            # We will map columns from the the source table onto the target table, based on their column name. This mapping will not consider the order of columns inside the tables, but will be solely based on column names. The same rules as for insert apply for this column mapping.
            # If any column from the source table does not have a corresponding column in the target table and is not referenced by the `condition` either, we will raise an error
            # This algorithm ensures that:
            #
            # we update all columns if they have a matching name
            # we bring mismatching columns to the users attention (e.g., if his column name is “userid” instead of “user_id”)
            # The update action is mapped to a SQL query of the form
            #
            # UPDATE target_db.<target-schema>.<target>
            # SET
            #    <target column 1> = <source column 1>,
            #    <target column 2> = <source column 2>,
            #    ...
            # FROM <source>
            # WHERE <condition>
            # -------
            json_request = {
                "actions": [
                    # UPDATE action
                    {
                        "action": "update",
                        "source-schema": "Extract",
                        "source-table": changeset_table_name,
                        "target-schema": "Extract",
                        "target-table": "Extract",
                        "condition": match_conditions_json,
                    },
                ]
            }
        elif action == "DELETE":
            # # The Delete operation deletes tuples from its target table.
            # It uses its `condition` to determine which tuples to delete.
            #
            # Example 1
            #
            # {"action": "delete",
            #  "target-table": "my_extract_table",
            #  "condition": {
            #    "op": "<",
            #    "target-col": "col1",
            #    "const": {"type": "datetime", "v": "2020-06-00"}}
            # }
            # Example 2
            #
            # {"action": "delete",
            #  "target-table": "my_extract_table",
            #  "source-table": "deleted_row_id_table",
            #  "condition": {"op": "=", "target-col": "id", "source-col": "deleted_id"}
            # }
            # Parameters:
            #
            # `target-table` (string; required): the table name inside the source database from which we will insert data
            # `target-schema` (string; required): analogous to source-schema, but for the source table
            # `source-table` (string; optional): the table name inside the target database into which the data will be inserted
            # `source-schema` (string; optional): the schema name inside the target database; default: the one, unique schema name inside the target database in case the target db has only one schema; error otherwise
            # `condition` (condition-specification; required): specifies the condition used to select the columns for deletion
            #
            # See separate section for the definition of `condition`s.
            #
            # If no `source` table is specified, the delete action will be translated to
            #
            # DELETE FROM target_db.<target-schema>.<target>
            # WHERE <condition>
            # This variant will be useful for “sliding window” extract, as described below in the examples section
            #
            # If a `source` table is specified, the delete action will be translated to
            #
            # DELETE FROM target_db.<target-schema>.<target>
            # WHERE EXISTS (
            #    SELECT * FROM <source-db>.<source-schema>.<source>
            #    WHERE <condition>
            # )
            # This variant is useful to delete many tuples, e.g., based on their row ID
            #
            # It is an error if the source table contains any additional columns not referenced by the condition. Those columns are pointless and we want to let the user know, so they can fix their scripts accordingly.
            if path_to_database is None:
                json_request = {
                    "actions": [
                        # UPDATE action
                        {
                            "action": "delete",
                            "target-schema": "Extract",
                            "target-table": "Extract",
                            "condition": match_conditions_json,
                        },
                    ]
                }
            else:
                json_request = {
                    "actions": [
                        # UPDATE action
                        {
                            "action": "delete",
                            "source-schema": "Extract",
                            "source-table": changeset_table_name,
                            "target-schema": "Extract",
                            "target-table": "Extract",
                            "condition": match_conditions_json,
                        },
                    ]
                }
        else:
            raise Exception(
                "Unknown action {} specified for update_datasource_from_hyper_file".format(
                    action
                )
            )
        file_upload_id = None
        if not path_to_database is None:
            # Update or delete by row_id
            file_upload_id = REST.upload_file(
                path_to_database,
                self.tableau_hostname,
                self.tableau_server.auth_token,
                self.tableau_server.site_id,
            )
        ds_id = self.get_datasource_id(tab_ds_name)
        async_job_id = REST.patch_datasource(
            server=self.tableau_hostname,
            auth_token=self.tableau_server.auth_token,
            site_id=self.tableau_server.site_id,
            datasource_id=ds_id,
            file_upload_id=file_upload_id,
            request_json=json_request,
        )
        finish_code = self.wait_for_async_job(async_job_id)
        if finish_code != "0":
            raise TableauJobError(
                "Patch job {} terminated with non-zero return code:{}".format(
                    async_job_id, finish_code
                )
            )

    @abstractmethod
    def hyper_sql_type(self, source_column):
        """
        Finds the correct Hyper column type for source_column

        source_column (obj): Source column descriptor

        Returns a tableauhyperapi.SqlType Object
        """

    @abstractmethod
    def hyper_table_definition(self, source_table, hyper_table_name="Extract"):
        """
        Build a hyper table definition from source_schema

        source_table (obj): Source table descriptor
        hyper_table_name (string): Name of the target Hyper table, default="Extract"

        Returns a tableauhyperapi.TableDefinition Object
        """

    @abstractmethod
    def query_to_hyper_files(self, sql_query, hyper_table_name="Extract"):
        """
        Executes sql_query against the source database and writes the output to one or more Hyper files
        Returns a list of output Hyper files

        sql_query (string): SQL to pass to the source database
        hyper_table_name (string): Name of the target Hyper table, default=Extract
        """

    @abstractmethod
    def load_sample(
        self,
        source_table,
        tab_ds_name,
        sample_rows=SAMPLE_ROWS,
        publish_mode=TSC.Server.PublishMode.CreateNew,
    ):
        """
        Loads a sample of rows from source_table to Tableau Server

        source_table (string): Source table identifier
        tab_ds_name (string): Target datasource name
        publish_mode: One of TSC.Server.[Overwrite|Append|CreateNew] (default=CreateNew)
        sample_rows (int): How many rows to include in the sample (default=SAMPLE_ROWS)
        """

    @abstractmethod
    def export_load(
        self, source_table, tab_ds_name, publish_mode=TSC.Server.PublishMode.CreateNew
    ):
        """
        Bulk export the contents of source_table and load to a Tableau Server

        source_table (string): Source table identifier
        tab_ds_name (string): Target datasource name
        publish_mode: One of TSC.Server.[Overwrite|Append|CreateNew] (default=CreateNew)
        """

    @abstractmethod
    def append_to_datasource(
        self, sql_query, tab_ds_name, publish_mode=TSC.Server.PublishMode.Append
    ):
        """
        Appends the result of sql_query to a datasource on Tableau Server

        source_table (string): Source table identifier
        tab_ds_name (string): Target datasource name
        publish_mode: One of TSC.Server.[Overwrite|Append|CreateNew] (default=Append)
        """

    @abstractmethod
    def update_datasource(
        self, sql_query, tab_ds_name, match_columns=None, match_conditions_json=None
    ):
        """
        Updates a datasource on Tableau Server with the changeset from sql_query

        sql_query (string): The query string that generates the changeset
        tab_ds_name (string): Target datasource name
        match_columns (array of tuples): Array of (source_col, target_col) pairs
        match_conditions_json (string): Define conditions for matching rows in json format.  See Hyper API guide for details.
        changeset_table_name (string): The name of the table in the hyper file that contains the changeset (default="updated_rows")

        NOTE: match_columns overrides match_conditions_json if both are specified
        """

    @abstractmethod
    def upsert_to_datasource(
        self, sql_query, tab_ds_name, match_columns=None, match_conditions_json=None
    ):
        """
        TODO: NOT IMPLEMENTED YET IN PRERELEASE
        Upsert/Merge the changeset from sql_query into a datasource on Tableau Server

        sql_query (string): The query string that generates the changeset
        tab_ds_name (string): Target datasource name
        match_columns (array of tuples): Array of (source_col, target_col) pairs
        match_conditions_json (string): Define conditions for matching rows in json format.  See Hyper API guide for details.
        changeset_table_name (string): The name of the table in the hyper file that contains the changeset (default="updated_rows")

        NOTE: match_columns overrides match_conditions_json if both are specified
        """

    @abstractmethod
    def delete_from_datasource(
        self,
        sql_query,
        tab_ds_name,
        match_columns=None,
        match_conditions_json=None,
        changeset_table_name="deleted_rowids",
    ):
        """
        Delete rows matching the changeset from sql_query from a datasource on Tableau Server
        Simple delete by condition when sql_query is None

        sql_query (string): The query string that generates the changeset
        tab_ds_name (string): Target datasource name
        match_columns (array of tuples): Array of (source_col, target_col) pairs
        match_conditions_json (string): Define conditions for matching rows in json format.  See Hyper API guide for details.
        changeset_table_name (string): The name of the table in the hyper file that contains the changeset (default="deleted_rowids")

        NOTES:
        - match_columns overrides match_conditions_json if both are specified
        - sql_query must only return columns referenced by the match condition
        - set sql_query to None if conditional delete
            (e.g. json_request="condition": { "op": "<", "target-col": "col1", "const": {"type": "datetime", "v": "2020-06-00"}})
        """


def main():
    pass


if __name__ == "__main__":
    main()
