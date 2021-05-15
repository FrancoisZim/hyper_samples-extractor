"""Google BigQuery implementation of Base Hyper Extractor ABC

Tableau Community supported Hyper API sample

-----------------------------------------------------------------------------

This file is the copyrighted property of Tableau Software and is protected
by registered patents and other applicable U.S. and international laws and
regulations.

You may adapt this file and modify it to fit into your context and use it
as a template to start your own projects.

-----------------------------------------------------------------------------
"""
import logging
import subprocess
import tableauserverclient as TSC
from tableauhyperapi import TableDefinition, Nullability, SqlType, TableName
from base_extractor import BaseExtractor, HyperSQLTypeMappingError, DEFAULT_SITE_ID

# from google.cloud.bigquery_storage import BigQueryReadClient
from google.cloud import bigquery
from google.cloud import storage

logger = logging.getLogger("hyper_samples.extractor.bigquery")

bq_client = bigquery.Client()

MAX_QUERY_SIZE = 100 * 1024 * 1024  # 100MB
SAMPLE_ROWS = 1000


class QuerySizeLimitError(Exception):
    pass


class BigQueryExtractor(BaseExtractor):
    """ Google BigQuery Implementation of Extractor Interface"""

    def __init__(
        self,
        tableau_username,
        tableau_password,
        tableau_hostname,
        tableau_project,
        staging_bucket,
        tableau_site_id=DEFAULT_SITE_ID,
    ):
        super().__init__(
            tableau_username,
            tableau_password,
            tableau_hostname,
            tableau_project,
            staging_bucket,
            tableau_site_id=tableau_site_id,
        )

    def hyper_sql_type(self, source_column):
        """
        Finds the correct Hyper column type for source_column

        source_column (obj): Source column (Instance of google.cloud.bigquery.schema.SchemaField)

        Returns a tableauhyperapi.SqlType Object
        """

        source_column_type = source_column.field_type
        return_sql_type = {
            "BOOL": SqlType.bool(),
            "BYTES": SqlType.bytes(),
            "DATE": SqlType.date(),
            "DATETIME": SqlType.timestamp(),
            "INT64": SqlType.big_int(),
            "INTEGER": SqlType.int(),
            "NUMERIC": SqlType.numeric(18, 9),
            "FLOAT64": SqlType.double(),
            "STRING": SqlType.text(),
            "TIME": SqlType.time(),
            "TIMESTAMP": SqlType.timestamp_tz(),
        }.get(source_column_type)

        if return_sql_type is None:
            error_message = "No Hyper SqlType defined for BigQuery source type: {}".format(
                source_column_type
            )
            logger.error(error_message)
            raise LookupError(error_message)

        logger.debug(
            "Translated source column type {} to Hyper SqlType {}".format(
                source_column_type, return_sql_type
            )
        )
        return return_sql_type

    def hyper_table_definition(self, source_table, hyper_table_name="Extract"):
        """
        Build a hyper table definition from source_schema

        source_table (obj): Source table (Instance of google.cloud.bigquery.table.Table)
        hyper_table_name (string): Name of the target Hyper table, default="Extract"

        Returns a tableauhyperapi.TableDefinition Object
        """

        logger.debug(
            "Building Hyper TableDefinition for table {}".format(source_table.reference)
        )
        target_cols = []
        for source_field in source_table.schema:
            this_name = source_field.name
            this_type = self.hyper_sql_type(source_field)
            this_col = TableDefinition.Column(name=this_name, type=this_type)

            # Check for Nullability
            this_mode = source_field.mode
            if this_mode == "REPEATED":
                raise (
                    HyperSQLTypeMappingError(
                        "Field mode REPEATED is not implemented in Hyper"
                    )
                )
            if this_mode == "REQUIRED":
                this_col = TableDefinition.Column(
                    this_name, this_type, Nullability.NOT_NULLABLE
                )

            target_cols.append(this_col)
            logger.debug("..Column {} - Type {}".format(this_name, this_type))

        target_schema = TableDefinition(
            table_name=TableName("Extract", hyper_table_name), columns=target_cols
        )

        return target_schema

    def query_to_hyper_files(self, sql_query, hyper_table_name="Extract"):
        """
        Executes sql_query against the source database and writes the output to one or more Hyper files
        Returns a list of output Hyper files

        sql_query -- SQL string to pass to the source database
        hyper_table_name -- Name of the target Hyper table, default=Extract
        """

        # Dry run to estimate result size
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        dryrun_query_job = bq_client.query(sql_query, job_config=job_config)
        dryrun_bytes_estimate = dryrun_query_job.total_bytes_processed
        logger.info("This query will process {} bytes.".format(dryrun_bytes_estimate))

        if dryrun_bytes_estimate > MAX_QUERY_SIZE:
            raise QuerySizeLimitError(
                "This query will return than {MAX_QUERY_SIZE} bytes"
            )

        query_job = bq_client.query(sql_query)

        # Determine table structure
        query_temp_table = bq_client.get_table(query_job.destination)
        target_table_def = self.hyper_table_definition(
            query_temp_table, hyper_table_name
        )

        def query_job_iter():
            return bq_client.list_rows(query_job.destination)

        return self.query_result_to_hyper_files(query_job_iter, target_table_def)

    def load_sample(
        self,
        source_table,
        tab_ds_name,
        sample_rows=SAMPLE_ROWS,
        publish_mode=TSC.Server.PublishMode.CreateNew,
    ):
        """
        Loads a sample of rows from source_table to Tableau Server

        source_table (string): Source table ref ("project ID.dataset ID.table ID")
        tab_ds_name (string): Target datasource name
        publish_mode: One of TSC.Server.[Overwrite|Append|CreateNew] (default=CreateNew)
        sample_rows (int): How many rows to include in the sample (default=SAMPLE_ROWS)
        """

        # loads in the first sample_rows of a bigquery table
        # set publish_mode=TSC.Server.PublishMode.Overwrite to refresh a sample
        sql_query = "SELECT * FROM `{}` LIMIT {}".format(source_table, sample_rows)
        output_hyper_files = self.query_to_hyper_files(sql_query, tab_ds_name)
        for path_to_database in output_hyper_files:
            self.publish_hyper_file(path_to_database, tab_ds_name, publish_mode)
            publish_mode = TSC.Server.PublishMode.Append  # Append subsequent chunks

    def export_load(
        self, source_table, tab_ds_name, publish_mode=TSC.Server.PublishMode.CreateNew
    ):
        """
        Bulk export the contents of source_table and load to a Tableau Server

        source_table (string): Source table ref ("project ID.dataset ID.table ID")
        tab_ds_name (string): Target datasource name
        publish_mode: One of TSC.Server.[Overwrite|Append|CreateNew] (default=CreateNew)
        """
        # Uses the bigquery export api to split large table to csv for load
        source_table_ref = bq_client.get_table(source_table)
        target_table_def = self.hyper_table_definition(source_table_ref)

        extract_job_config = bigquery.ExtractJobConfig(
            compression="GZIP", destination_format="CSV"
        )

        extract_prefix = "staging/{}".format(source_table)
        extract_destination_uri = "gs://{}/{}-*.csv.gz".format(
            self.staging_bucket, extract_prefix
        )
        extract_job = bq_client.extract_table(
            source_table, extract_destination_uri, job_config=extract_job_config
        )  # API request
        extract_job.result()  # Waits for job to complete.
        logger.info("Exported {} to {}".format(source_table, extract_destination_uri))

        storage_client = storage.Client()
        bucket = storage_client.bucket(self.staging_bucket)
        for blob in bucket.list_blobs(prefix=extract_prefix):
            logger.info("Downloading blob:{}".format(blob))
            temp_csv_filename = "temp.csv"
            blob.download_to_filename("{}.gz".format(temp_csv_filename))
            # # TODO: better error checking here
            subprocess.run(["gunzip", "{}.gz".format(temp_csv_filename)], check=True)
            output_hyper_files = self.csv_to_hyper_files(
                temp_csv_filename, target_table_def
            )
            subprocess.run(["rm", temp_csv_filename], check=True)
            for path_to_database in output_hyper_files:
                self.publish_hyper_file(path_to_database, tab_ds_name, publish_mode)
                subprocess.run(["rm", path_to_database], check=True)
                publish_mode = TSC.Server.PublishMode.Append  # Append subsequent chunks

    def append_to_datasource(
        self, sql_query, tab_ds_name, publish_mode=TSC.Server.PublishMode.Append
    ):
        """
        Appends the result of sql_query to a datasource on Tableau Server

        source_table (string): Source table identifier
        tab_ds_name (string): Target datasource name
        publish_mode: One of TSC.Server.[Overwrite|Append|CreateNew] (default=Append)
        """
        output_hyper_files = self.query_to_hyper_files(sql_query, tab_ds_name)
        for path_to_database in output_hyper_files:
            self.publish_hyper_file(path_to_database, tab_ds_name, publish_mode)
            publish_mode = TSC.Server.PublishMode.Append  # Append subsequent chunks

    def update_datasource(
        self,
        sql_query,
        tab_ds_name,
        match_columns=None,
        match_conditions_json=None,
        changeset_table_name="updated_rows",
    ):
        """
        Updates a datasource on Tableau Server with the changeset from sql_query

        sql_query (string): The query string that generates the changeset
        tab_ds_name (string): Target datasource name
        match_columns (array of tuples): Array of (source_col, target_col) pairs
        match_conditions_json (string): Define conditions for matching rows in json format.
            See Hyper API guide for details.
        changeset_table_name (string): The name of the table in the hyper file that contains
            the changeset (default="updated_rows")

        NOTE: match_columns overrides match_conditions_json if both are specified
        """
        output_hyper_files = self.query_to_hyper_files(sql_query, changeset_table_name)
        for path_to_database in output_hyper_files:
            self.update_datasource_from_hyper_file(
                path_to_database,
                tab_ds_name,
                match_columns,
                match_conditions_json,
                changeset_table_name,
            )

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
        match_conditions_json (string): Define conditions for matching rows in json format.
            See Hyper API guide for details.
        changeset_table_name (string): The name of the table in the hyper file that contains
            the changeset (default="deleted_rowids")

        NOTES:
        - match_columns overrides match_conditions_json if both are specified
        - sql_query must only return columns referenced by the match condition
        - set sql_query to None if conditional delete
            (e.g. json_request="condition": { "op": "<", "target-col": "col1",
            "const": {"type": "datetime", "v": "2020-06-00"}})
        """
        if sql_query is None:
            self.update_datasource_from_hyper_file(
                None, tab_ds_name, None, match_conditions_json, None,
            )
        else:
            output_hyper_files = self.query_to_hyper_files(
                sql_query, changeset_table_name
            )
            for path_to_database in output_hyper_files:
                self.update_datasource_from_hyper_file(
                    path_to_database,
                    tab_ds_name,
                    match_columns,
                    match_conditions_json,
                    changeset_table_name,
                )


def main():
    pass


if __name__ == "__main__":
    main()
