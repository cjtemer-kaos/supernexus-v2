Transcriptformer Tools
======================

**Configuration File**: ``remote_tools/transcriptformer_tools.json``
**Tool Type**: Remote
**Tools Count**: 1

This page contains all tools defined in the ``transcriptformer_tools.json`` configuration file.

Available Tools
---------------

**run_transcriptformer_embedding_retrieval** (Type: RemoteTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves contextualized gene embeddings from Transcriptformer models. This tool provides access ...

.. dropdown:: run_transcriptformer_embedding_retrieval tool specification

   **Tool Information:**

   * **Name**: ``run_transcriptformer_embedding_retrieval``
   * **Type**: ``RemoteTool``
   * **Description**: Retrieves contextualized gene embeddings from Transcriptformer models. This tool provides access to pre-computed Transcriptformer embeddings that capture gene expression patterns learned from single-cell RNA sequencing data. The embeddings are contextualized for specific combinations of disease states and cell types, enabling precise analysis of gene behavior in relevant biological contexts.

   **Parameters:**

   * ``state`` (string) (required)
     Disease state context for embedding retrieval. Examples: 'control': Healthy/normal condition; 'disease': Disease-affected state; 'treated': Post-treatment condition; 'untreated': Pre-treatment condition. Must match available states in the disease-specific store.

   * ``cell_type`` (string) (required)
     Cell type context for embeddings. Examples: 'b_cell': B lymphocytes; 't_cell': T lymphocytes; 'macrophage': Tissue macrophages; 'epithelial_cell': Epithelial cells; 'fibroblast': Connective tissue fibroblasts. Must match available cell types in the disease store.

   * ``gene_names`` (array) (required)
     Gene identifiers for embedding retrieval: Gene symbols: ['TP53', 'BRCA1', 'EGFR', 'MYC']; Ensembl IDs: ['ENSG00000141510', 'ENSG00000139618']; Mixed formats supported; Empty list retrieves all available genes.

   * ``disease`` (string) (required)
     Disease/dataset identifier. Examples: 'breast_cancer': Breast cancer scRNA-seq data; 'lung_cancer': Lung cancer contexts; 'diabetes': Diabetes-related datasets; 'alzheimer': Alzheimer's disease contexts. Must match available disease stores.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "run_transcriptformer_embedding_retrieval",
          "arguments": {
              "state": "example_value",
              "cell_type": "example_value",
              "gene_names": ["item1", "item2"],
              "disease": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`remote_tools` - Remote Tools Setup
