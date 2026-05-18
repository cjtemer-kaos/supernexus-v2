Arxiv Tools
===========

**Configuration File**: ``arxiv_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``arxiv_tools.json`` configuration file.

Available Tools
---------------

**ArXiv_search_papers** (Type: ArXivTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search arXiv for papers by keyword using the public arXiv API. Returns papers with title, abstrac...

.. dropdown:: ArXiv_search_papers tool specification

   **Tool Information:**

   * **Name**: ``ArXiv_search_papers``
   * **Type**: ``ArXivTool``
   * **Description**: Search arXiv for papers by keyword using the public arXiv API. Returns papers with title, abstract, authors, publication date, category, and URL.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for arXiv papers. Use keywords separated by spaces to refine your search.

   * ``limit`` (integer) (optional)
     Number of papers to return. This sets the maximum number of papers retrieved from arXiv.

   * ``sort_by`` (string) (optional)
     Sort order for results. Options: 'relevance', 'lastUpdatedDate', 'submittedDate'

   * ``sort_order`` (string) (optional)
     Sort direction. Options: 'ascending', 'descending'

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ArXiv_search_papers",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
