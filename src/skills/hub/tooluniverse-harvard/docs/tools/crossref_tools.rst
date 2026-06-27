Crossref Tools
==============

**Configuration File**: ``crossref_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``crossref_tools.json`` configuration file.

Available Tools
---------------

**Crossref_search_works** (Type: CrossrefTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Crossref Works API for articles by keyword. Returns articles with title, abstract, journal...

.. dropdown:: Crossref_search_works tool specification

   **Tool Information:**

   * **Name**: ``Crossref_search_works``
   * **Type**: ``CrossrefTool``
   * **Description**: Search Crossref Works API for articles by keyword. Returns articles with title, abstract, journal, year, DOI, and URL. Supports filtering by publication type and date range.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for Crossref works. Use keywords separated by spaces to refine your search.

   * ``limit`` (integer) (required)
     Number of articles to return. This sets the maximum number of articles retrieved from Crossref.

   * ``filter`` (string) (required)
     Optional filter string for Crossref API. Examples: 'type:journal-article,from-pub-date:2020-01-01'

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Crossref_search_works",
          "arguments": {
              "query": "example_value",
              "limit": 10,
              "filter": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
