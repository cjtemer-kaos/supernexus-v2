Pubtator Tools
==============

**Configuration File**: ``pubtator_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``pubtator_tools.json`` configuration file.

Available Tools
---------------

**PubTator3_EntityAutocomplete** (Type: PubTatorTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides suggestions for the best‐matching standardized PubTator IDs for a partial biomedical ter...

.. dropdown:: PubTator3_EntityAutocomplete tool specification

   **Tool Information:**

   * **Name**: ``PubTator3_EntityAutocomplete``
   * **Type**: ``PubTatorTool``
   * **Description**: Provides suggestions for the best‐matching standardized PubTator IDs for a partial biomedical term (gene, disease, chemical, or variant). Use this tool first to convert free‐text names into the stable @IDs required by the other PubTator APIs.

   **Parameters:**

   * ``text`` (string) (required)
     A few characters or the full name of the biomedical concept you are trying to look up (e.g. “BRAF V6”).

   * ``entity_type`` (string) (required)
     Optional filter to restrict suggestions to a single category such as GENE, DISEASE, CHEMICAL, or VARIANT.

   * ``max_results`` (integer) (required)
     Maximum number of suggestions to return (1 - 50, default = 10).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubTator3_EntityAutocomplete",
          "arguments": {
              "text": "example_value",
              "entity_type": "example_value",
              "max_results": 10
          }
      }
      result = tu.run(query)


**PubTator3_LiteratureSearch** (Type: PubTatorTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find PubMed articles that match a keyword, a PubTator entity ID (e.g. “@GENE_BRAF”), or an entity...

.. dropdown:: PubTator3_LiteratureSearch tool specification

   **Tool Information:**

   * **Name**: ``PubTator3_LiteratureSearch``
   * **Type**: ``PubTatorTool``
   * **Description**: Find PubMed articles that match a keyword, a PubTator entity ID (e.g. “@GENE_BRAF”), or an entity-to-entity relation expression (e.g. “relations:treat|@CHEMICAL_Doxorubicin|@DISEASE_Neoplasms”).

   **Parameters:**

   * ``query`` (string) (required)
     What you want to search for. This can be plain keywords, a single PubTator ID, or the special relation syntax shown above.

   * ``page`` (integer) (required)
     Zero-based results page (optional; default = 0).

   * ``page_size`` (integer) (required)
     How many PMIDs to return per page (optional; default = 20, maximum = 200).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubTator3_LiteratureSearch",
          "arguments": {
              "query": "example_value",
              "page": 10,
              "page_size": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
