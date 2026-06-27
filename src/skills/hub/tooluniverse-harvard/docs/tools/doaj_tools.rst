Doaj Tools
==========

**Configuration File**: ``doaj_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``doaj_tools.json`` configuration file.

Available Tools
---------------

**DOAJ_search_articles** (Type: DOAJTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search DOAJ (Directory of Open Access Journals) for open-access articles. Returns articles with t...

.. dropdown:: DOAJ_search_articles tool specification

   **Tool Information:**

   * **Name**: ``DOAJ_search_articles``
   * **Type**: ``DOAJTool``
   * **Description**: Search DOAJ (Directory of Open Access Journals) for open-access articles. Returns articles with title, authors, year, DOI, venue, and URL.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for DOAJ articles. Supports Lucene syntax for advanced queries.

   * ``max_results`` (integer) (optional)
     Maximum number of articles to return. Default is 10, maximum is 100.

   * ``type`` (string) (optional)
     Type of search: 'articles' or 'journals'. Default is 'articles'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DOAJ_search_articles",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
