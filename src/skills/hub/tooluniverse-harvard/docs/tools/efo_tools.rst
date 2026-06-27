Efo Tools
=========

**Configuration File**: ``efo_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``efo_tools.json`` configuration file.

Available Tools
---------------

**OSL_get_efo_id_by_disease_name** (Type: EFOTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tool to lookup Experimental Factor Ontology (EFO) IDs for diseases via the EMBL-EBI OLS API.

.. dropdown:: OSL_get_efo_id_by_disease_name tool specification

   **Tool Information:**

   * **Name**: ``OSL_get_efo_id_by_disease_name``
   * **Type**: ``EFOTool``
   * **Description**: Tool to lookup Experimental Factor Ontology (EFO) IDs for diseases via the EMBL-EBI OLS API.

   **Parameters:**

   * ``disease`` (string) (required)
     Search query for diseases. Provide the disease name to lookup the corresponding EFO ID.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OSL_get_efo_id_by_disease_name",
          "arguments": {
              "disease": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
