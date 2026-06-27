Medrxiv Tools
=============

**Configuration File**: ``medrxiv_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``medrxiv_tools.json`` configuration file.

Available Tools
---------------

**MedRxiv_search_preprints** (Type: MedRxivTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search medRxiv preprints using the public medRxiv API. Returns preprints with title, authors, yea...

.. dropdown:: MedRxiv_search_preprints tool specification

   **Tool Information:**

   * **Name**: ``MedRxiv_search_preprints``
   * **Type**: ``MedRxivTool``
   * **Description**: Search medRxiv preprints using the public medRxiv API. Returns preprints with title, authors, year, DOI, and URL.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for medRxiv preprints. Use keywords separated by spaces to refine your search.

   * ``max_results`` (integer) (required)
     Maximum number of preprints to return. Default is 10, maximum is 200.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedRxiv_search_preprints",
          "arguments": {
              "query": "example_value",
              "max_results": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
