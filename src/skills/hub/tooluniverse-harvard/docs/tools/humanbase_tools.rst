Humanbase Tools
===============

**Configuration File**: ``humanbase_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``humanbase_tools.json`` configuration file.

Available Tools
---------------

**humanbase_ppi_analysis** (Type: HumanBaseTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve tissue-specific protein-protein interactions and biological processes from HumanBase. Re...

.. dropdown:: humanbase_ppi_analysis tool specification

   **Tool Information:**

   * **Name**: ``humanbase_ppi_analysis``
   * **Type**: ``HumanBaseTool``
   * **Description**: Retrieve tissue-specific protein-protein interactions and biological processes from HumanBase. Returns a NetworkX graph of tissue specific protein-protein interactions and a list of associated biological processes involeed by the given genes from Gene Ontology.

   **Parameters:**

   * ``gene_list`` (array) (required)
     List of gene names or symbols to analyze for protein-protein interactions. The gene name should be the official gene symbol, not the synonym.

   * ``tissue`` (string) (required)
     Tissue type for tissue-specific interactions. Examples: 'brain', 'heart', 'liver', 'kidney', etc.

   * ``max_node`` (integer) (required)
     Maximum number of nodes to retrieve in the interaction network. Warning: the more nodes, the more time it takes to retrieve the data. Default is 10 (~30 seconds).

   * ``interaction`` (string) (required)
     Specific interaction type to filter by. Available types: 'co-expression', 'interaction', 'tf-binding', 'gsea-microrna-targets', 'gsea-perturbations'. If not specified, all types will be included.

   * ``string_mode`` (boolean) (required)
     Whether to return the result in string mode. If True, the result will be a string of the network graph and the biological processes. If False, the result will be a NetworkX graph and a list of biological processes.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "humanbase_ppi_analysis",
          "arguments": {
              "gene_list": ["item1", "item2"],
              "tissue": "example_value",
              "max_node": 10,
              "interaction": "example_value",
              "string_mode": true
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
