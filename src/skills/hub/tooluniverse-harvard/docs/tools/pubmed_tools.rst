Pubmed Tools
============

**Configuration File**: ``pubmed_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``pubmed_tools.json`` configuration file.

Available Tools
---------------

**PubMed_search_articles** (Type: PubMedTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search PubMed using NCBI E-utilities (esearch + esummary) and return articles. Returns articles w...

.. dropdown:: PubMed_search_articles tool specification

   **Tool Information:**

   * **Name**: ``PubMed_search_articles``
   * **Type**: ``PubMedTool``
   * **Description**: Search PubMed using NCBI E-utilities (esearch + esummary) and return articles. Returns articles with title, journal, year, DOI, and PubMed URL.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for PubMed articles. Use keywords separated by spaces to refine your search.

   * ``limit`` (integer) (optional)
     Number of articles to return. This sets the maximum number of articles retrieved from PubMed.

   * ``api_key`` (string) (optional)
     Optional NCBI API key for higher rate limits. Get your free key at https://www.ncbi.nlm.nih.gov/account/

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubMed_search_articles",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
