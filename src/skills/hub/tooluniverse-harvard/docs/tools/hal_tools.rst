Hal Tools
=========

**Configuration File**: ``hal_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``hal_tools.json`` configuration file.

Available Tools
---------------

**HAL_search_archive** (Type: HALTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search the French HAL open archive via its public API. Returns documents with title, authors, yea...

.. dropdown:: HAL_search_archive tool specification

   **Tool Information:**

   * **Name**: ``HAL_search_archive``
   * **Type**: ``HALTool``
   * **Description**: Search the French HAL open archive via its public API. Returns documents with title, authors, year, DOI, URL, abstract, and source.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for HAL archive. Supports Lucene syntax for advanced queries.

   * ``max_results`` (integer) (required)
     Maximum number of documents to return. Default is 10, maximum is 100.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HAL_search_archive",
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
