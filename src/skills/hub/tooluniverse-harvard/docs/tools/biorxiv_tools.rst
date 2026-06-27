Biorxiv Tools
=============

**Configuration File**: ``biorxiv_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``biorxiv_tools.json`` configuration file.

Available Tools
---------------

**BioRxiv_search_preprints** (Type: BioRxivTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search bioRxiv preprints using the public bioRxiv API. Returns preprints with title, authors, yea...

.. dropdown:: BioRxiv_search_preprints tool specification

   **Tool Information:**

   * **Name**: ``BioRxiv_search_preprints``
   * **Type**: ``BioRxivTool``
   * **Description**: Search bioRxiv preprints using the public bioRxiv API. Returns preprints with title, authors, year, DOI, and URL.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for bioRxiv preprints. Use keywords separated by spaces to refine your search.

   * ``max_results`` (integer) (required)
     Maximum number of preprints to return. Default is 10, maximum is 200.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "BioRxiv_search_preprints",
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
