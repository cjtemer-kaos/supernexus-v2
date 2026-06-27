Txagent Client Tools
====================

**Configuration File**: ``txagent_client_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``txagent_client_tools.json`` configuration file.

Available Tools
---------------

**mcp_auto_loader_txagent** (Type: MCPAutoLoaderTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automatically discover and load all tools from TxAgent MCP Server. Can register discovered tools ...

.. dropdown:: mcp_auto_loader_txagent tool specification

   **Tool Information:**

   * **Name**: ``mcp_auto_loader_txagent``
   * **Type**: ``MCPAutoLoaderTool``
   * **Description**: Automatically discover and load all tools from TxAgent MCP Server. Can register discovered tools as individual ToolUniverse tools or provide tool configurations.

   **Parameters:** No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "mcp_auto_loader_txagent",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
