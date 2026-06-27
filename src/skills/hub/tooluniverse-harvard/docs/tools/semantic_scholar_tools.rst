Semantic Scholar Tools
======================

**Configuration File**: ``semantic_scholar_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``semantic_scholar_tools.json`` configuration file.

Available Tools
---------------

**SemanticScholar_search_papers** (Type: SemanticScholarTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for papers on Semantic Scholar including abstracts. This tool queries the Semantic Scholar...

.. dropdown:: SemanticScholar_search_papers tool specification

   **Tool Information:**

   * **Name**: ``SemanticScholar_search_papers``
   * **Type**: ``SemanticScholarTool``
   * **Description**: Search for papers on Semantic Scholar including abstracts. This tool queries the Semantic Scholar API using natural language keywords and returns papers with details such as title, abstract, publication year, journal (venue), and URL.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for Semantic Scholar. Use keywords separated by spaces to refine the search.

   * ``limit`` (integer) (required)
     Maximum number of papers to return from Semantic Scholar.

   * ``api_key`` (string) (optional)
     Optional API key for Semantic Scholar to obtain a higher quota.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "SemanticScholar_search_papers",
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
