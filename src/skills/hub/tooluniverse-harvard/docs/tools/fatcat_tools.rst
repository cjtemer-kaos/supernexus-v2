Fatcat Tools
============

**Configuration File**: ``fatcat_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``fatcat_tools.json`` configuration file.

Available Tools
---------------

**Fatcat_search_scholar** (Type: FatcatScholarTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Internet Archive Scholar via Fatcat releases search. Fatcat is the underlying database pow...

.. dropdown:: Fatcat_search_scholar tool specification

   **Tool Information:**

   * **Name**: ``Fatcat_search_scholar``
   * **Type**: ``FatcatScholarTool``
   * **Description**: Search Internet Archive Scholar via Fatcat releases search. Fatcat is the underlying database powering Internet Archive Scholar, providing access to millions of research papers and academic publications.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for Fatcat releases. Use keywords to search across titles, abstracts, and metadata of research papers.

   * ``max_results`` (integer) (required)
     Maximum number of results to return. Default is 10, maximum is 100.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Fatcat_search_scholar",
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
