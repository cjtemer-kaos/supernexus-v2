Pubchem Tools
=============

**Configuration File**: ``pubchem_tools.json``
**Tool Type**: Local
**Tools Count**: 9

This page contains all tools defined in the ``pubchem_tools.json`` configuration file.

Available Tools
---------------

**PubChem_get_CID_by_SMILES** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve corresponding CID list by SMILES string.

.. dropdown:: PubChem_get_CID_by_SMILES tool specification

   **Tool Information:**

   * **Name**: ``PubChem_get_CID_by_SMILES``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Retrieve corresponding CID list by SMILES string.

   **Parameters:**

   * ``smiles`` (string) (required)
     SMILES expression (e.g., "CC(=O)OC1=CC=CC=C1C(=O)O" corresponds to aspirin).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_get_CID_by_SMILES",
          "arguments": {
              "smiles": "example_value"
          }
      }
      result = tu.run(query)


**PubChem_get_CID_by_compound_name** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve corresponding CID list (IdentifierList) by chemical name.

.. dropdown:: PubChem_get_CID_by_compound_name tool specification

   **Tool Information:**

   * **Name**: ``PubChem_get_CID_by_compound_name``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Retrieve corresponding CID list (IdentifierList) by chemical name.

   **Parameters:**

   * ``name`` (string) (required)
     Chemical name (e.g., "Aspirin" or IUPAC name).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_get_CID_by_compound_name",
          "arguments": {
              "name": "example_value"
          }
      }
      result = tu.run(query)


**PubChem_get_associated_patents_by_CID** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get a list of patents associated with a specific compound CID.

.. dropdown:: PubChem_get_associated_patents_by_CID tool specification

   **Tool Information:**

   * **Name**: ``PubChem_get_associated_patents_by_CID``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Get a list of patents associated with a specific compound CID.

   **Parameters:**

   * ``cid`` (integer) (required)
     PubChem compound ID to query, e.g., 2244 (Aspirin).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_get_associated_patents_by_CID",
          "arguments": {
              "cid": 10
          }
      }
      result = tu.run(query)


**PubChem_get_compound_2D_image_by_CID** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get 2D structure image (PNG format) of compound by CID.

.. dropdown:: PubChem_get_compound_2D_image_by_CID tool specification

   **Tool Information:**

   * **Name**: ``PubChem_get_compound_2D_image_by_CID``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Get 2D structure image (PNG format) of compound by CID.

   **Parameters:**

   * ``cid`` (integer) (required)
     Compound ID to get image for, e.g., 2244.

   * ``image_size`` (string) (required)
     Optional parameter, image size, like "200x200" (default).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_get_compound_2D_image_by_CID",
          "arguments": {
              "cid": 10,
              "image_size": "example_value"
          }
      }
      result = tu.run(query)


**PubChem_get_compound_properties_by_CID** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get a set of specified molecular properties through CID (Compound ID), such as molecular weight, ...

.. dropdown:: PubChem_get_compound_properties_by_CID tool specification

   **Tool Information:**

   * **Name**: ``PubChem_get_compound_properties_by_CID``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Get a set of specified molecular properties through CID (Compound ID), such as molecular weight, IUPAC name, Canonical SMILES.

   **Parameters:**

   * ``cid`` (integer) (required)
     PubChem compound ID to query, e.g., 2244 (Aspirin).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_get_compound_properties_by_CID",
          "arguments": {
              "cid": 10
          }
      }
      result = tu.run(query)


**PubChem_get_compound_synonyms_by_CID** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get complete list of synonyms for compound by CID.

.. dropdown:: PubChem_get_compound_synonyms_by_CID tool specification

   **Tool Information:**

   * **Name**: ``PubChem_get_compound_synonyms_by_CID``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Get complete list of synonyms for compound by CID.

   **Parameters:**

   * ``cid`` (integer) (required)
     Compound ID to query synonyms for, e.g., 2244.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_get_compound_synonyms_by_CID",
          "arguments": {
              "cid": 10
          }
      }
      result = tu.run(query)


**PubChem_get_compound_xrefs_by_CID** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get external references (XRefs) for compound by CID, including links to ChEBI, DrugBank, KEGG, etc.

.. dropdown:: PubChem_get_compound_xrefs_by_CID tool specification

   **Tool Information:**

   * **Name**: ``PubChem_get_compound_xrefs_by_CID``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Get external references (XRefs) for compound by CID, including links to ChEBI, DrugBank, KEGG, etc.

   **Parameters:**

   * ``cid`` (integer) (required)
     Compound ID to query external references for, e.g., 2244.

   * ``xref_types`` (array) (required)
     List of external database types to query, e.g., ["RegistryID", "RN", "PubMedID"].

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_get_compound_xrefs_by_CID",
          "arguments": {
              "cid": 10,
              "xref_types": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**PubChem_search_compounds_by_similarity** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search by similarity (Tanimoto coefficient), returns CID list of compounds with similarity above ...

.. dropdown:: PubChem_search_compounds_by_similarity tool specification

   **Tool Information:**

   * **Name**: ``PubChem_search_compounds_by_similarity``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Search by similarity (Tanimoto coefficient), returns CID list of compounds with similarity above threshold to given SMILES molecule, returns no more than 10 CIDs (MaxRecords=10)

   **Parameters:**

   * ``smiles`` (string) (required)
     SMILES expression of target molecule.

   * ``threshold`` (number) (required)
     Similarity threshold (between 0 and 1), e.g., 0.9 means 90% similarity.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_search_compounds_by_similarity",
          "arguments": {
              "smiles": "example_value",
              "threshold": "example_value"
          }
      }
      result = tu.run(query)


**PubChem_search_compounds_by_substructure** (Type: PubChemRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for all CIDs in PubChem that contain the given substructure (SMILES).

.. dropdown:: PubChem_search_compounds_by_substructure tool specification

   **Tool Information:**

   * **Name**: ``PubChem_search_compounds_by_substructure``
   * **Type**: ``PubChemRESTTool``
   * **Description**: Search for all CIDs in PubChem that contain the given substructure (SMILES).

   **Parameters:**

   * ``smiles`` (string) (required)
     SMILES of substructure (e.g., "c1ccccc1" corresponds to benzene ring).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubChem_search_compounds_by_substructure",
          "arguments": {
              "smiles": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
