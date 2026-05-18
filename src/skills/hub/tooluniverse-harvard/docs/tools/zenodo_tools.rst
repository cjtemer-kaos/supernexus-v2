Zenodo Tools
============

**Configuration File**: ``zenodo_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``zenodo_tools.json`` configuration file.

Available Tools
---------------

**Zenodo_search_records** (Type: ZenodoTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Zenodo for research data, publications, and datasets. Zenodo is an open-access repository ...

.. dropdown:: Zenodo_search_records tool specification

   **Tool Information:**

   * **Name**: ``Zenodo_search_records``
   * **Type**: ``ZenodoTool``
   * **Description**: Search Zenodo for research data, publications, and datasets. Zenodo is an open-access repository that hosts research outputs from all fields of science, including papers, datasets, software, and more.

   **Parameters:**

   * ``query`` (string) (required)
     Free text search query for Zenodo records. Use keywords to search across titles, descriptions, authors, and other metadata.

   * ``max_results`` (integer) (required)
     Maximum number of results to return. Must be between 1 and 200.

   * ``community`` (string) (optional)
     Optional community slug to filter results by specific research community (e.g., 'zenodo', 'ecfunded').

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Zenodo_search_records",
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
