Wikidata Sparql Tools
=====================

**Configuration File**: ``wikidata_sparql_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``wikidata_sparql_tools.json`` configuration file.

Available Tools
---------------

**Wikidata_SPARQL_query** (Type: WikidataSPARQLTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute SPARQL queries against Wikidata to retrieve structured data. This tool powers Scholia-sty...

.. dropdown:: Wikidata_SPARQL_query tool specification

   **Tool Information:**

   * **Name**: ``Wikidata_SPARQL_query``
   * **Type**: ``WikidataSPARQLTool``
   * **Description**: Execute SPARQL queries against Wikidata to retrieve structured data. This tool powers Scholia-style visualizations and can query academic topics, authors, institutions, and research relationships.

   **Parameters:**

   * ``sparql`` (string) (required)
     SPARQL query string to execute against Wikidata. Use SPARQL syntax to query academic entities, relationships, and properties.

   * ``max_results`` (integer) (required)
     Optional result limit override. If not specified, uses the LIMIT clause in the SPARQL query or returns all results.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Wikidata_SPARQL_query",
          "arguments": {
              "sparql": "example_value",
              "max_results": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
