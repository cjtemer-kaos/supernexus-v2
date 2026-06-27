Dailymed Tools
==============

**Configuration File**: ``dailymed_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``dailymed_tools.json`` configuration file.

Available Tools
---------------

**DailyMed_get_spl_by_setid** (Type: GetSPLBySetIDTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get complete label corresponding to SPL Set ID, returns content in XML or JSON format.

.. dropdown:: DailyMed_get_spl_by_setid tool specification

   **Tool Information:**

   * **Name**: ``DailyMed_get_spl_by_setid``
   * **Type**: ``GetSPLBySetIDTool``
   * **Description**: Get complete label corresponding to SPL Set ID, returns content in XML or JSON format.

   **Parameters:**

   * ``setid`` (string) (required)
     SPL Set ID to query.

   * ``format`` (string) (required)
     Return format, only supports 'xml'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DailyMed_get_spl_by_setid",
          "arguments": {
              "setid": "example_value",
              "format": "example_value"
          }
      }
      result = tu.run(query)


**DailyMed_search_spls** (Type: SearchSPLTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search SPL list using multiple filter conditions (drug_name/ndc/rxcui/setid) and return metadata ...

.. dropdown:: DailyMed_search_spls tool specification

   **Tool Information:**

   * **Name**: ``DailyMed_search_spls``
   * **Type**: ``SearchSPLTool``
   * **Description**: Search SPL list using multiple filter conditions (drug_name/ndc/rxcui/setid) and return metadata + data array.

   **Parameters:**

   * ``drug_name`` (string) (required)
     Generic or brand name of the drug, e.g., 'TAMSULOSIN HYDROCHLORIDE'.

   * ``ndc`` (string) (required)
     National Drug Code (NDC).

   * ``rxcui`` (string) (required)
     RxNorm Code (RXCUI).

   * ``setid`` (string) (required)
     Set ID corresponding to the SPL.

   * ``published_date_gte`` (string) (required)
     Published date >= specified date, format 'YYYY-MM-DD'.

   * ``published_date_eq`` (string) (required)
     Published date == specified date, format 'YYYY-MM-DD'.

   * ``pagesize`` (integer) (required)
     Number of items per page, maximum 100, default 100.

   * ``page`` (integer) (required)
     Page number, starts from 1, default 1.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DailyMed_search_spls",
          "arguments": {
              "drug_name": "example_value",
              "ndc": "example_value",
              "rxcui": "example_value",
              "setid": "example_value",
              "published_date_gte": "example_value",
              "published_date_eq": "example_value",
              "pagesize": 10,
              "page": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
