Dblp Tools
==========

**Configuration File**: ``dblp_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``dblp_tools.json`` configuration file.

Available Tools
---------------

**DBLP_search_publications** (Type: DBLPTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search DBLP Computer Science Bibliography for publications. Returns publications with title, auth...

.. dropdown:: DBLP_search_publications tool specification

   **Tool Information:**

   * **Name**: ``DBLP_search_publications``
   * **Type**: ``DBLPTool``
   * **Description**: Search DBLP Computer Science Bibliography for publications. Returns publications with title, authors, year, venue, URL, and electronic edition link.

   **Parameters:**

   * ``query`` (string) (required)
     Search query for DBLP publications. Use keywords separated by spaces to refine your search.

   * ``limit`` (integer) (required)
     Number of publications to return. This sets the maximum number of publications retrieved from DBLP.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DBLP_search_publications",
          "arguments": {
              "query": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
