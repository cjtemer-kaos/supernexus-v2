Core Tools
==========

**Configuration File**: ``core_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``core_tools.json`` configuration file.

Available Tools
---------------

**CORE_search_papers** (Type: CoreTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for open access academic papers using CORE API. CORE is the world's largest collection of ...

.. dropdown:: CORE_search_papers tool specification

   **Tool Information:**

   * **Name**: ``CORE_search_papers``
   * **Type**: ``CoreTool``
   * **Description**: Search for open access academic papers using CORE API. CORE is the world's largest collection of open access research papers, providing access to over 200 million papers from repositories and journals worldwide.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for CORE papers. Use keywords separated by spaces to refine your search.

   * ``limit`` (integer) (required)
     Maximum number of papers to return. This sets the maximum number of papers retrieved from CORE.

   * ``year_from`` (integer) (optional)
     Start year for publication date filter (e.g., 2020). Optional parameter to limit search to papers published from this year onwards.

   * ``year_to`` (integer) (optional)
     End year for publication date filter (e.g., 2024). Optional parameter to limit search to papers published up to this year.

   * ``language`` (string) (optional)
     Language filter for papers (e.g., 'en', 'es', 'fr'). Optional parameter to limit search to papers in specific language.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "CORE_search_papers",
          "arguments": {
              "query": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
