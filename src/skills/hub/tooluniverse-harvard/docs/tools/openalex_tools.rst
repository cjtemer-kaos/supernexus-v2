Openalex Tools
==============

**Configuration File**: ``openalex_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``openalex_tools.json`` configuration file.

Available Tools
---------------

**openalex_literature_search** (Type: OpenAlexTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for academic literature using OpenAlex API. Retrieves papers with title, abstract, authors...

.. dropdown:: openalex_literature_search tool specification

   **Tool Information:**

   * **Name**: ``openalex_literature_search``
   * **Type**: ``OpenAlexTool``
   * **Description**: Search for academic literature using OpenAlex API. Retrieves papers with title, abstract, authors, publication year, and organizational affiliations based on search keywords.

   **Parameters:**

   * ``search_keywords`` (string) (required)
     Keywords to search for in paper titles, abstracts, and content. Use relevant scientific terms or phrases.

   * ``max_results`` (integer) (optional)
     Maximum number of papers to retrieve (default: 10, maximum: 200).

   * ``year_from`` (integer) (optional)
     Start year for publication date filter (e.g., 2020). Optional parameter to limit search to papers published from this year onwards.

   * ``year_to`` (integer) (optional)
     End year for publication date filter (e.g., 2023). Optional parameter to limit search to papers published up to this year.

   * ``open_access`` (boolean) (optional)
     Filter for open access papers only. Set to true for open access papers, false for non-open access, or omit for all papers.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "openalex_literature_search",
          "arguments": {
              "search_keywords": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
