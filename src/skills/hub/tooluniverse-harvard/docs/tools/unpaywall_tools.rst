Unpaywall Tools
===============

**Configuration File**: ``unpaywall_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``unpaywall_tools.json`` configuration file.

Available Tools
---------------

**Unpaywall_check_oa_status** (Type: UnpaywallTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query Unpaywall by DOI to check open-access status and OA locations. Requires a contact email for...

.. dropdown:: Unpaywall_check_oa_status tool specification

   **Tool Information:**

   * **Name**: ``Unpaywall_check_oa_status``
   * **Type**: ``UnpaywallTool``
   * **Description**: Query Unpaywall by DOI to check open-access status and OA locations. Requires a contact email for API access.

   **Parameters:**

   * ``doi`` (string) (required)
     DOI (Digital Object Identifier) of the article to check for open access status.

   * ``email`` (string) (required)
     Contact email address required by Unpaywall API for polite usage tracking.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Unpaywall_check_oa_status",
          "arguments": {
              "doi": "example_value",
              "email": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
