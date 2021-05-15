<img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70">


# Hyper API Sample: Cloud Database Extractor functionality
[![Community Supported](https://img.shields.io/badge/Support%20Level-Community%20Supported-457387.svg)](https://www.tableau.com/support-levels-it-and-developer-tools)

<br  />

usage: extractor_cli.py [-h] [--extractor {bigquery}]
                        [--source_table_id SOURCE_TABLE_ID]
                        [--tableau_project TABLEAU_PROJECT]
                        [--tableau_datasource TABLEAU_DATASOURCE]
                        [--tableau_hostname TABLEAU_HOSTNAME]
                        [--tableau_site_id TABLEAU_SITE_ID] [--bucket BUCKET]
                        [--sample_rows SAMPLE_ROWS] [--sql SQL]
                        [--sqlfile SQLFILE]
                        [--match_columns MATCH_COLUMNS MATCH_COLUMNS]
                        [--match_conditions_json MATCH_CONDITIONS_JSON]
                        --tableau_username TABLEAU_USERNAME
                        {load_sample,export_load,append,update,delete}

Utilities to build Hyper Extracts from Cloud Databases
* load_sample: Load sample rows of data to new Tableau datasource
* export_load: Bulk export and load to new Tableau datasource
* append: Append the results of a query to an existing Tableau datasource
* update: Update an existing Tableau datasource with the changeset from a query
* delete: Delete rows from a Tableau datasource that match key columns in a changeset from a query

positional arguments:
  {load_sample,export_load,append,update,delete}
                        Select the utility function to call
optional arguments:
  -h, --help            show this help message and exit
  --extractor {bigquery}
                        Select the extractor implementation that matches your
                        cloud database
  --source_table_id SOURCE_TABLE_ID
                        Source table id (default=pre-sales-
                        demo.EU_Superstore.Orders)
  --tableau_project TABLEAU_PROJECT, -P TABLEAU_PROJECT
                        Target project name (default=HyperAPITests)
  --tableau_datasource TABLEAU_DATASOURCE
                        Target datasource name (default=Orders)
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

<br  />

## Requirements: ##

* [Hyper API for Python](https://help.tableau.com/current/api/hyper_api/en-us/docs/hyper_api_installing.html#install-the-hyper-api-for-python-36-and-37)
* [Tableau Server Client Libraries](https://help.tableau.com/current/api/hyper_api/en-us/docs/hyper_api_installing.html#install-the-hyper-api-for-python-36-and-37)
* BigQuery Extractor: The google cloud sdk and python libraries for Cloud Storage and BigQuery

### __If you are looking to learn more about the Hyper API, please check out the [official documentation](https://help.tableau.com/current/api/hyper_api/en-us/index.html).__ ###

<br  />

## What is the Hyper API?
For the unfamiliar, the Hyper API contains a set of functions you can use to automate your interactions with Tableau extract (.hyper) files. You can use the API to create new extract files, or to open existing files, and then insert, delete, update, or read data from those files. Using the Hyper API developers and administrators can:
* Create extract files for data sources not currently supported by Tableau.
* Automate custom extract, transform and load (ETL) processes (for example, implement rolling window updates or custom incremental updates).
* Retrieve data from an extract file.



## How do I install the Hyper API?
It is a prerequisite that to work with these code samples, the Hyper API is installed in your language of choice. Head to our [official Hyper API Documentation](https://help.tableau.com/current/api/hyper_api/en-us/docs/hyper_api_installing.html) to get it up and running.

## Hyper API License
Note that the Hyper API comes with a proprietary license, see the `LICENSE` file in the Hyper API package.
