Reactome Tools
==============

**Configuration File**: ``reactome_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``reactome_tools.json`` configuration file.

Available Tools
---------------

**Reactome_get_pathway_reactions** (Type: ReactomeRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query all Reactions contained under a Pathway using Pathway Stable ID. This is currently the only...

.. dropdown:: Reactome_get_pathway_reactions tool specification

   **Tool Information:**

   * **Name**: ``Reactome_get_pathway_reactions``
   * **Type**: ``ReactomeRESTTool``
   * **Description**: Query all Reactions contained under a Pathway using Pathway Stable ID. This is currently the only working Reactome tool.

   **Parameters:**

   * ``stId`` (string) (required)
     Pathway Stable ID, e.g., 'R-HSA-73817' (verified valid).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Reactome_get_pathway_reactions",
          "arguments": {
              "stId": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
