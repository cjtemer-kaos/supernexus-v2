Url Fetch Tools
===============

**Configuration File**: ``url_fetch_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``url_fetch_tools.json`` configuration file.

Available Tools
---------------

**get_webpage_text_from_url** (Type: URLToPDFTextTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Render a URL as PDF and extract its text (JavaScript supported).

.. dropdown:: get_webpage_text_from_url tool specification

   **Tool Information:**

   * **Name**: ``get_webpage_text_from_url``
   * **Type**: ``URLToPDFTextTool``
   * **Description**: Render a URL as PDF and extract its text (JavaScript supported).

   **Parameters:**

   * ``url`` (string) (required)
     Webpage URL to fetch and render

   * ``timeout`` (integer) (required)
     Request timeout in seconds

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_webpage_text_from_url",
          "arguments": {
              "url": "example_value",
              "timeout": 10
          }
      }
      result = tu.run(query)


**get_webpage_title** (Type: URLHTMLTagTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch a webpage and return the content of its <title> tag.

.. dropdown:: get_webpage_title tool specification

   **Tool Information:**

   * **Name**: ``get_webpage_title``
   * **Type**: ``URLHTMLTagTool``
   * **Description**: Fetch a webpage and return the content of its <title> tag.

   **Parameters:**

   * ``url`` (string) (required)
     HTTP or HTTPS URL to fetch (e.g. https://www.example.com)

   * ``timeout`` (integer) (required)
     Request timeout in seconds

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_webpage_title",
          "arguments": {
              "url": "example_value",
              "timeout": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
