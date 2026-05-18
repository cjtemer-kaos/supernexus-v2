Osf Preprints Tools
===================

**Configuration File**: ``osf_preprints_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``osf_preprints_tools.json`` configuration file.

Available Tools
---------------

**OSF_search_preprints** (Type: OSFPreprintsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search OSF (Open Science Framework) Preprints for research preprints and working papers. OSF Prep...

.. dropdown:: OSF_search_preprints tool specification

   **Tool Information:**

   * **Name**: ``OSF_search_preprints``
   * **Type**: ``OSFPreprintsTool``
   * **Description**: Search OSF (Open Science Framework) Preprints for research preprints and working papers. OSF Preprints aggregates preprints from multiple providers including OSF, PsyArXiv, and others.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for OSF preprints. Use keywords to search across titles and abstracts.

   * ``max_results`` (integer) (required)
     Maximum number of results to return. Default is 10, maximum is 100.

   * ``provider`` (string) (required)
     Optional preprint provider filter (e.g., 'osf', 'psyarxiv', 'socarxiv'). If not specified, searches all providers.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OSF_search_preprints",
          "arguments": {
              "query": "example_value",
              "max_results": 10,
              "provider": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
