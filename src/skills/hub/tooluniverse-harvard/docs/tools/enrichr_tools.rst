Enrichr Tools
=============

**Configuration File**: ``enrichr_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``enrichr_tools.json`` configuration file.

Available Tools
---------------

**enrichr_gene_enrichment_analysis** (Type: EnrichrTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Perform gene enrichment analysis using Enrichr to find biological pathways, processes, and molecu...

.. dropdown:: enrichr_gene_enrichment_analysis tool specification

   **Tool Information:**

   * **Name**: ``enrichr_gene_enrichment_analysis``
   * **Type**: ``EnrichrTool``
   * **Description**: Perform gene enrichment analysis using Enrichr to find biological pathways, processes, and molecular functions associated with a list of genes. Returns connectivity paths between genes and enrichment terms.

   **Parameters:**

   * ``gene_list`` (array) (required)
     List of gene names or symbols to analyze. At least 2 genes are required for path ranking analysis.

   * ``libs`` (array) (required)
     List of enrichment libraries to use for analysis.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "enrichr_gene_enrichment_analysis",
          "arguments": {
              "gene_list": ["item1", "item2"],
              "libs": ["item1", "item2"]
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
