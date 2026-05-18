Europe Pmc Tools
================

**Configuration File**: ``europe_pmc_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``europe_pmc_tools.json`` configuration file.

Available Tools
---------------

**EuropePMC_search_articles** (Type: EuropePMCTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for articles on Europe PMC including abstracts. The tool queries the Europe PMC web servic...

.. dropdown:: EuropePMC_search_articles tool specification

   **Tool Information:**

   * **Name**: ``EuropePMC_search_articles``
   * **Type**: ``EuropePMCTool``
   * **Description**: Search for articles on Europe PMC including abstracts. The tool queries the Europe PMC web service using provided keywords and returns articles with details such as title, abstract, journal, publication year, and a URL to the full article.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for Europe PMC. Use keywords separated by spaces to refine your search.

   * ``limit`` (integer) (optional)
     Number of articles to return. This sets the maximum number of articles retrieved from Europe PMC.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "EuropePMC_search_articles",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
