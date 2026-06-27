Uspto Downloader Tools
======================

**Configuration File**: ``remote_tools/uspto_downloader_tools.json``
**Tool Type**: Remote
**Tools Count**: 3

This page contains all tools defined in the ``uspto_downloader_tools.json`` configuration file.

Available Tools
---------------

**get_abstract_from_patent_app_number** (Type: RemoteTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the abstract (ABST) text for a given patent application number.

.. dropdown:: get_abstract_from_patent_app_number tool specification

   **Tool Information:**

   * **Name**: ``get_abstract_from_patent_app_number``
   * **Type**: ``RemoteTool``
   * **Description**: Returns the abstract (ABST) text for a given patent application number.

   **Parameters:**

   * ``applicationNumberText`` (string) (required)
     The USPTO application number (e.g. "19113417").

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_abstract_from_patent_app_number",
          "arguments": {
              "applicationNumberText": "example_value"
          }
      }
      result = tu.run(query)


**get_claims_from_patent_app_number** (Type: RemoteTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the claims (CLM) text for a given patent application number.

.. dropdown:: get_claims_from_patent_app_number tool specification

   **Tool Information:**

   * **Name**: ``get_claims_from_patent_app_number``
   * **Type**: ``RemoteTool``
   * **Description**: Returns the claims (CLM) text for a given patent application number.

   **Parameters:**

   * ``applicationNumberText`` (string) (required)
     The USPTO application number (e.g. "19113417").

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_claims_from_patent_app_number",
          "arguments": {
              "applicationNumberText": "example_value"
          }
      }
      result = tu.run(query)


**get_full_text_from_patent_app_number** (Type: RemoteTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the full application text for a given patent application number.

.. dropdown:: get_full_text_from_patent_app_number tool specification

   **Tool Information:**

   * **Name**: ``get_full_text_from_patent_app_number``
   * **Type**: ``RemoteTool``
   * **Description**: Returns the full application text for a given patent application number.

   **Parameters:**

   * ``applicationNumberText`` (string) (required)
     The USPTO application number (e.g. "19113417").

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_full_text_from_patent_app_number",
          "arguments": {
              "applicationNumberText": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`remote_tools` - Remote Tools Setup
