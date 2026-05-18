Gene Ontology Tools
===================

**Configuration File**: ``gene_ontology_tools.json``
**Tool Type**: Local
**Tools Count**: 5

This page contains all tools defined in the ``gene_ontology_tools.json`` configuration file.

Available Tools
---------------

**GO_get_annotations_for_gene** (Type: GeneOntologyTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finds all GO annotations for a specific gene/protein using GOlr search.

.. dropdown:: GO_get_annotations_for_gene tool specification

   **Tool Information:**

   * **Name**: ``GO_get_annotations_for_gene``
   * **Type**: ``GeneOntologyTool``
   * **Description**: Finds all GO annotations for a specific gene/protein using GOlr search.

   **Parameters:**

   * ``gene_id`` (string) (required)
     A gene identifier such as gene symbol (e.g., 'TP53') or database ID.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GO_get_annotations_for_gene",
          "arguments": {
              "gene_id": "example_value"
          }
      }
      result = tu.run(query)


**GO_get_genes_for_term** (Type: GeneOntologyTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finds all genes/proteins associated with a specific Gene Ontology term using the Biolink API.

.. dropdown:: GO_get_genes_for_term tool specification

   **Tool Information:**

   * **Name**: ``GO_get_genes_for_term``
   * **Type**: ``GeneOntologyTool``
   * **Description**: Finds all genes/proteins associated with a specific Gene Ontology term using the Biolink API.

   **Parameters:**

   * ``id`` (string) (required)
     The standard GO term ID, e.g., 'GO:0006915'.

   * ``taxon`` (string) (required)
     Optional species filter using a NCBI taxon ID. For example, Human is 'NCBITaxon:9606', and Mouse is 'NCBITaxon:10090'.

   * ``rows`` (integer) (required)
     The number of genes to return. Default is 100.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GO_get_genes_for_term",
          "arguments": {
              "id": "example_value",
              "taxon": "example_value",
              "rows": 10
          }
      }
      result = tu.run(query)


**GO_get_term_by_id** (Type: GeneOntologyTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves basic GO term information by ID using GOlr search.

.. dropdown:: GO_get_term_by_id tool specification

   **Tool Information:**

   * **Name**: ``GO_get_term_by_id``
   * **Type**: ``GeneOntologyTool``
   * **Description**: Retrieves basic GO term information by ID using GOlr search.

   **Parameters:**

   * ``id`` (string) (required)
     The standard GO term ID, e.g., 'GO:0006915' for apoptotic process.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GO_get_term_by_id",
          "arguments": {
              "id": "example_value"
          }
      }
      result = tu.run(query)


**GO_get_term_details** (Type: GeneOntologyTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves detailed information for a specific GO ID using the Biolink API, including definition, ...

.. dropdown:: GO_get_term_details tool specification

   **Tool Information:**

   * **Name**: ``GO_get_term_details``
   * **Type**: ``GeneOntologyTool``
   * **Description**: Retrieves detailed information for a specific GO ID using the Biolink API, including definition, synonyms, and annotations.

   **Parameters:**

   * ``id`` (string) (required)
     The standard GO term ID, e.g., 'GO:0006915' for apoptotic process.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GO_get_term_details",
          "arguments": {
              "id": "example_value"
          }
      }
      result = tu.run(query)


**GO_search_terms** (Type: GeneOntologyTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Searches for Gene Ontology (GO) terms by a keyword using the GOlr search engine. Returns GO terms...

.. dropdown:: GO_search_terms tool specification

   **Tool Information:**

   * **Name**: ``GO_search_terms``
   * **Type**: ``GeneOntologyTool``
   * **Description**: Searches for Gene Ontology (GO) terms by a keyword using the GOlr search engine. Returns GO terms and related biological entities.

   **Parameters:**

   * ``query`` (string) (required)
     The keyword to search for, e.g., 'apoptosis' or 'kinase activity'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GO_search_terms",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
