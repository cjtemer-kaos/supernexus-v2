Markitdown Tools
================

**Configuration File**: ``markitdown_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``markitdown_tools.json`` configuration file.

Available Tools
---------------

**convert_to_markdown** (Type: MarkItDownTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert a resource described by an http:, https:, file: or data: URI to markdown.

.. dropdown:: convert_to_markdown tool specification

   **Tool Information:**

   * **Name**: ``convert_to_markdown``
   * **Type**: ``MarkItDownTool``
   * **Description**: Convert a resource described by an http:, https:, file: or data: URI to markdown.

   **Parameters:**

   * ``uri`` (string) (required)
     URI of the resource to convert (supports http:, https:, file:, data: URIs)

   * ``output_path`` (string) (optional)
     Optional output file path

   * ``enable_plugins`` (boolean) (optional)
     Enable 3rd-party plugins

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "convert_to_markdown",
          "arguments": {
              "uri": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
