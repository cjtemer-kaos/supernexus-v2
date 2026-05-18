Medlineplus Tools
=================

**Configuration File**: ``medlineplus_tools.json``
**Tool Type**: Local
**Tools Count**: 5

This page contains all tools defined in the ``medlineplus_tools.json`` configuration file.

Available Tools
---------------

**MedlinePlus_connect_lookup_by_code** (Type: MedlinePlusRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Look up corresponding MedlinePlus page information through MedlinePlus Connect Web Service using ...

.. dropdown:: MedlinePlus_connect_lookup_by_code tool specification

   **Tool Information:**

   * **Name**: ``MedlinePlus_connect_lookup_by_code``
   * **Type**: ``MedlinePlusRESTTool``
   * **Description**: Look up corresponding MedlinePlus page information through MedlinePlus Connect Web Service using clinical/drug/test codes (such as ICD-10 CM, RXCUI, LOINC, etc.), supports JSON or XML format return.

   **Parameters:**

   * ``cs`` (string) (required)
     Code system OID, e.g., ICD-10 CM=2.16.840.1.113883.6.90, RXCUI=2.16.840.1.113883.6.88, LOINC=2.16.840.1.113883.6.1, etc.

   * ``c`` (string) (required)
     Specific code value to query, e.g., "E11.9" (ICD-10 CM) or "637188" (RXCUI).

   * ``dn`` (string) (required)
     Optional, descriptive name (English) corresponding to the code, for drugs can fill in "Chantix 0.5 MG Oral Tablet", can improve matching accuracy.

   * ``language`` (string) (required)
     Return information language, "en" for English, "es" for Spanish, default "en".

   * ``format`` (string) (required)
     Return format, options "json" or "xml", default "json".

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedlinePlus_connect_lookup_by_code",
          "arguments": {
              "cs": "example_value",
              "c": "example_value",
              "dn": "example_value",
              "language": "example_value",
              "format": "example_value"
          }
      }
      result = tu.run(query)


**MedlinePlus_get_genetics_condition_by_name** (Type: MedlinePlusRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information from MedlinePlus Genetics corresponding to genetic condition name, suppo...

.. dropdown:: MedlinePlus_get_genetics_condition_by_name tool specification

   **Tool Information:**

   * **Name**: ``MedlinePlus_get_genetics_condition_by_name``
   * **Type**: ``MedlinePlusRESTTool``
   * **Description**: Get detailed information from MedlinePlus Genetics corresponding to genetic condition name, supports JSON or XML format return.

   **Parameters:**

   * ``condition`` (string) (required)
     URL slug of genetic condition, e.g., "alzheimer-disease", must match MedlinePlus page path.

   * ``format`` (string) (required)
     Return format, options "json" or "xml", default "json".

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedlinePlus_get_genetics_condition_by_name",
          "arguments": {
              "condition": "example_value",
              "format": "example_value"
          }
      }
      result = tu.run(query)


**MedlinePlus_get_genetics_gene_by_name** (Type: MedlinePlusRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information from MedlinePlus Genetics corresponding to gene name, supports JSON or X...

.. dropdown:: MedlinePlus_get_genetics_gene_by_name tool specification

   **Tool Information:**

   * **Name**: ``MedlinePlus_get_genetics_gene_by_name``
   * **Type**: ``MedlinePlusRESTTool``
   * **Description**: Get detailed information from MedlinePlus Genetics corresponding to gene name, supports JSON or XML format return.

   **Parameters:**

   * ``gene`` (string) (required)
     URL slug of gene name, e.g., "BRCA1", must match MedlinePlus page path.

   * ``format`` (string) (required)
     Return format, options "json" or "xml", default "json".

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedlinePlus_get_genetics_gene_by_name",
          "arguments": {
              "gene": "example_value",
              "format": "example_value"
          }
      }
      result = tu.run(query)


**MedlinePlus_get_genetics_index** (Type: MedlinePlusRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download index file (XML) of all genetics entries in MedlinePlus, get complete list in one call.

.. dropdown:: MedlinePlus_get_genetics_index tool specification

   **Tool Information:**

   * **Name**: ``MedlinePlus_get_genetics_index``
   * **Type**: ``MedlinePlusRESTTool``
   * **Description**: Download index file (XML) of all genetics entries in MedlinePlus, get complete list in one call.

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedlinePlus_get_genetics_index",
          "arguments": {
          }
      }
      result = tu.run(query)


**MedlinePlus_search_topics_by_keyword** (Type: MedlinePlusRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for relevant information in MedlinePlus Web Service by keyword across health topics or oth...

.. dropdown:: MedlinePlus_search_topics_by_keyword tool specification

   **Tool Information:**

   * **Name**: ``MedlinePlus_search_topics_by_keyword``
   * **Type**: ``MedlinePlusRESTTool``
   * **Description**: Search for relevant information in MedlinePlus Web Service by keyword across health topics or other sub-libraries (such as drugs, genetics, etc.).

   **Parameters:**

   * ``term`` (string) (required)
     Search keyword, e.g., "diabetes", needs to be URL encoded before passing.

   * ``db`` (string) (required)
     Specify the database to search, e.g., healthTopics (English health topics), healthTopicsSpanish (Spanish health topics), drugs (English drugs), etc.

   * ``rettype`` (string) (required)
     Result return format, options: brief (concise information, default), topic (detailed XML record), all (includes all available information).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedlinePlus_search_topics_by_keyword",
          "arguments": {
              "term": "example_value",
              "db": "example_value",
              "rettype": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
