Ppi Tools
=========

**Configuration File**: ``ppi_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``ppi_tools.json`` configuration file.

Available Tools
---------------

**BioGRID_get_interactions** (Type: BioGRIDRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query protein and genetic interactions from the BioGRID database. BioGRID is a comprehensive data...

.. dropdown:: BioGRID_get_interactions tool specification

   **Tool Information:**

   * **Name**: ``BioGRID_get_interactions``
   * **Type**: ``BioGRIDRESTTool``
   * **Description**: Query protein and genetic interactions from the BioGRID database. BioGRID is a comprehensive database of physical and genetic interactions with detailed experimental evidence.

   **Parameters:**

   * ``gene_names`` (array) (required)
     List of gene names or protein identifiers

   * ``organism`` (string) (optional)
     Organism name (e.g., 'Homo sapiens', 'Mus musculus')

   * ``interaction_type`` (string) (optional)
     Type of interaction ('physical', 'genetic', 'both')

   * ``evidence_types`` (array) (optional)
     List of evidence types to include

   * ``limit`` (integer) (optional)
     Maximum number of interactions to return (default: 100)

   * ``format`` (string) (optional)
     Output format ('json' or 'tab', default: 'json')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "BioGRID_get_interactions",
          "arguments": {
              "gene_names": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**STRING_get_protein_interactions** (Type: STRINGRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query protein-protein interactions from the STRING database. STRING is a comprehensive database o...

.. dropdown:: STRING_get_protein_interactions tool specification

   **Tool Information:**

   * **Name**: ``STRING_get_protein_interactions``
   * **Type**: ``STRINGRESTTool``
   * **Description**: Query protein-protein interactions from the STRING database. STRING is a comprehensive database of known and predicted protein-protein interactions with confidence scores and functional annotations.

   **Parameters:**

   * ``protein_ids`` (array) (required)
     List of protein identifiers (UniProt IDs, gene names, etc.)

   * ``species`` (integer) (optional)
     NCBI taxonomy ID (default: 9606 for human)

   * ``confidence_score`` (number) (optional)
     Minimum confidence score (0-1, default: 0.4)

   * ``limit`` (integer) (optional)
     Maximum number of interactions to return (default: 50)

   * ``network_type`` (string) (optional)
     Type of network ('full', 'physical', 'functional')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "STRING_get_protein_interactions",
          "arguments": {
              "protein_ids": ["item1", "item2"]
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
