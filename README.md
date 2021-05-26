<img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70">


# Hyper API Sample: Cloud Database Extractor Utility
[![Community Supported](https://img.shields.io/badge/Support%20Level-Community%20Supported-457387.svg)](https://www.tableau.com/support-levels-it-and-developer-tools)

## Overview
This package defines a standard Extractor Interface which is extended by specific implementations
to support specific cloud databases.  For most use cases you will probably only ever call the
following methods:
* load_sample - Loads a sample of rows from source_table to Tableau Server
* export_load - Bulk export the contents of source_table and load to a Tableau Server
* append_to_datasource - Appends the result of sql_query to a datasource on Tableau Server
* update_datasource - Updates a datasource on Tableau Server with the changeset from sql_query
* delete_from_datasource - Delete rows matching the changeset from a datasource on Tableau Server.  Simple delete by condition when sql_query is None

For a full list of methods and args see the docstrings in the BaseExtractor class.

## Contents
* base_extractor.py - provies an Abstract Base Class with some utility methods to extract from cloud databases to "live to hyper" Tableau Datasources. Database specific Extractor classes extend this to manage queries, exports and schema discovery via the database vendor supplied client libraries.

* bigquery_extractor - Google BigQuery implementation of Base Hyper Extractor ABC

* restapi_helpers - The helper functions in this module are only used when REST API functionality is not yet available in the standard tableauserverclient libraries. (e.g. PATCH for update/upsert. Once these get added to the standard client libraries then this module will be refactored out.

* extractor_cli - Simple CLI Wrapper around Extractor Classes

## CLI Utility
We suggest that you import one of the Extractor implementations and call this directly however we've included a command line utility to illustrate the key functionality:


>$ python3 extractor_cli.py --help
usage: extractor_cli.py [-h] [--extractor {bigquery}]
                        [--source_table_id SOURCE_TABLE_ID]
                        [--tableau_project TABLEAU_PROJECT]
                        --tableau_datasource TABLEAU_DATASOURCE
                        [--tableau_hostname TABLEAU_HOSTNAME]
                        [--tableau_site_id TABLEAU_SITE_ID] [--bucket BUCKET]
                        [--sample_rows SAMPLE_ROWS] [--sql SQL]
                        [--sqlfile SQLFILE]
                        [--match_columns MATCH_COLUMNS MATCH_COLUMNS]
                        [--match_conditions_json MATCH_CONDITIONS_JSON]
                        [--tableau_username TABLEAU_USERNAME]
                        [--tableau_token_name TABLEAU_TOKEN_NAME]
                        [--tableau_token_secretfile TABLEAU_TOKEN_SECRETFILE]
                        {load_sample,export_load,append,update,delete}

Utilities to build Hyper Extracts from Cloud Databases
* load_sample: Load sample rows of data to new Tableau datasource
* export_load: Bulk export and load to new Tableau datasource
* append: Append the results of a query to an existing Tableau datasource
* update: Update an existing Tableau datasource with the changeset from a query
* delete: Delete rows from a Tableau datasource that match key columns in a changeset from a query

>
>positional arguments:
  {load_sample,export_load,append,update,delete}
                        Select the utility function to call
>
>optional arguments:
  -h, --help            show this help message and exit
  --extractor {bigquery}
                        Select the extractor implementation that matches your
                        cloud database
  --source_table_id SOURCE_TABLE_ID
                        Source table ID
  --tableau_project TABLEAU_PROJECT, -P TABLEAU_PROJECT
                        Target project name (default=HyperAPITests)
  --tableau_datasource TABLEAU_DATASOURCE
                        Target datasource name
  --tableau_hostname TABLEAU_HOSTNAME, -H TABLEAU_HOSTNAME
                        Tableau connection string (default=http://localhost)
  --tableau_site_id TABLEAU_SITE_ID, -S TABLEAU_SITE_ID
                        Tableau site id (default=)
  --bucket BUCKET       Bucket used for extract staging storage
                        (default=emea_se)
  --sample_rows SAMPLE_ROWS
                        Defines the number of rows to use with LIMIT when
                        command=load_sample (default=1000)
  --sql SQL             The query string used to generate the changeset when
                        command=[append|update|merge]
  --sqlfile SQLFILE     File containing the query string used to generate the
                        changeset when command=[append|update|delete]
  --match_columns MATCH_COLUMNS MATCH_COLUMNS
                        Define conditions for matching source and target key
                        columns to use when command=[update|delete]. Specify
                        one or more column pairs in the format:
                        --match_columns [source_col] [target_col]
  --match_conditions_json MATCH_CONDITIONS_JSON
                        Define conditions for matching rows in json format
                        when command=[update|delete].See Hyper API guide for
                        details.
  --tableau_username TABLEAU_USERNAME, -U TABLEAU_USERNAME
                        Tableau user name
  --tableau_token_name TABLEAU_TOKEN_NAME
                        Personal access token name
  --tableau_token_secretfile TABLEAU_TOKEN_SECRETFILE
                        File containing personal access token secret


## Requirements: ##
* [Hyper API for Python](https://help.tableau.com/current/api/hyper_api/en-us/docs/hyper_api_installing.html#install-the-hyper-api-for-python-36-and-37)
* [Tableau Server Client Libraries](https://help.tableau.com/current/api/hyper_api/en-us/docs/hyper_api_installing.html#install-the-hyper-api-for-python-36-and-37)
* BigQuery Extractor: The `Google Cloud SDK` and `Python libraries for Cloud Storage and BigQuery`

### __If you are looking to learn more about the Hyper API, please check out the [official documentation](https://help.tableau.com/current/api/hyper_api/en-us/index.html).__ ###
