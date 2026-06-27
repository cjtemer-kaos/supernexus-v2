Pmc Tools
=========

**Configuration File**: ``pmc_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``pmc_tools.json`` configuration file.

Available Tools
---------------

**PMC_search_papers** (Type: PMCTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for full-text biomedical literature using PMC (PubMed Central) API. PMC is the free full-t...

.. dropdown:: PMC_search_papers tool specification

   **Tool Information:**

   * **Name**: ``PMC_search_papers``
   * **Type**: ``PMCTool``
   * **Description**: Search for full-text biomedical literature using PMC (PubMed Central) API. PMC is the free full-text archive of biomedical and life sciences journal literature at the U.S. National Institutes of Health's National Library of Medicine.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for PMC papers. Use keywords separated by spaces to refine your search.

   * ``limit`` (integer) (required)
     Maximum number of papers to return. This sets the maximum number of papers retrieved from PMC.

   * ``date_from`` (string) (optional)
     Start date for publication date filter (YYYY/MM/DD format). Optional parameter to limit search to papers published from this date onwards.

   * ``date_to`` (string) (optional)
     End date for publication date filter (YYYY/MM/DD format). Optional parameter to limit search to papers published up to this date.

   * ``article_type`` (string) (optional)
     Article type filter (e.g., 'research-article', 'review', 'case-report'). Optional parameter to limit search to specific article types.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PMC_search_papers",
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
