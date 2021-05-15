<img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70"><img src="https://cdns.tblsft.com/sites/default/files/blog/hyper_logo_1.jpg" width="70" height="70">


# Hyper API Sample: Cloud Database Extractor Utility
[![Community Supported](https://img.shields.io/badge/Support%20Level-Community%20Supported-457387.svg)](https://www.tableau.com/support-levels-it-and-developer-tools)

We suggest that you import one of the Extractor implementations and call this directly however we've included a command line utility to illustrate the key functionality:

>USAGE: extractor_cli.py [-h] {load_sample|export_load|append|update|delete}
>[--extractor {bigquery}]
>[--source_table_id SOURCE_TABLE_ID]
>[--tableau_project TABLEAU_PROJECT]
>[--tableau_datasource TABLEAU_DATASOURCE]
>[--tableau_hostname TABLEAU_HOSTNAME]
>[--tableau_site_id TABLEAU_SITE_ID] [--bucket BUCKET]
>[--sample_rows SAMPLE_ROWS] [--sql SQL]
>[--sqlfile SQLFILE]
>[--match_columns MATCH_COLUMNS MATCH_COLUMNS]
>[--match_conditions_json MATCH_CONDITIONS_JSON]
>--tableau_username TABLEAU_USERNAME

Utilities to build Hyper Extracts from Cloud Databases
* load_sample: Load sample rows of data to new Tableau datasource
* export_load: Bulk export and load to new Tableau datasource
* append: Append the results of a query to an existing Tableau datasource
* update: Update an existing Tableau datasource with the changeset from a query
* delete: Delete rows from a Tableau datasource that match key columns in a changeset from a query


## Requirements: ##
* [Hyper API for Python](https://help.tableau.com/current/api/hyper_api/en-us/docs/hyper_api_installing.html#install-the-hyper-api-for-python-36-and-37)
* [Tableau Server Client Libraries](https://help.tableau.com/current/api/hyper_api/en-us/docs/hyper_api_installing.html#install-the-hyper-api-for-python-36-and-37)
* BigQuery Extractor: The `Google Cloud SDK` and `Python libraries for Cloud Storage and BigQuery`

### __If you are looking to learn more about the Hyper API, please check out the [official documentation](https://help.tableau.com/current/api/hyper_api/en-us/index.html).__ ###
