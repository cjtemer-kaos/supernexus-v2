Mcp Client Tools Example
========================

**Configuration File**: ``mcp_client_tools_example.json``
**Tool Type**: Local
**Tools Count**: 4

This page contains all tools defined in the ``mcp_client_tools_example.json`` configuration file.

Available Tools
---------------

**mcp_auto_loader_server1** (Type: MCPAutoLoaderTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automatically discover and load all tools from MCP Server 1. Can register discovered tools as ind...

.. dropdown:: mcp_auto_loader_server1 tool specification

   **Tool Information:**

   * **Name**: ``mcp_auto_loader_server1``
   * **Type**: ``MCPAutoLoaderTool``
   * **Description**: Automatically discover and load all tools from MCP Server 1. Can register discovered tools as individual ToolUniverse tools or provide tool configurations.

   **Parameters:** No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "mcp_auto_loader_server1",
          "arguments": {
          }
      }
      result = tu.run(query)


**mcp_client_example** (Type: MCPClientTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Example MCP client to connect to an existing MCP server. Supports all MCP operations including to...

.. dropdown:: mcp_client_example tool specification

   **Tool Information:**

   * **Name**: ``mcp_client_example``
   * **Type**: ``MCPClientTool``
   * **Description**: Example MCP client to connect to an existing MCP server. Supports all MCP operations including tools, resources, and prompts.

   **Parameters:**

   * ``operation`` (string) (required)
     The MCP operation to perform

   * ``tool_name`` (string) (required)
     Name of the tool to call (required for call_tool operation)

   * ``tool_arguments`` (object) (required)
     Arguments to pass to the tool (for call_tool operation)

   * ``uri`` (string) (required)
     Resource URI (required for read_resource operation)

   * ``prompt_name`` (string) (required)
     Name of the prompt to get (required for get_prompt operation)

   * ``prompt_arguments`` (object) (required)
     Arguments to pass to the prompt (for get_prompt operation)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "mcp_client_example",
          "arguments": {
              "operation": "example_value",
              "tool_name": "example_value",
              "tool_arguments": "example_value",
              "uri": "example_value",
              "prompt_name": "example_value",
              "prompt_arguments": "example_value"
          }
      }
      result = tu.run(query)


**mcp_mock_calculator** (Type: MCPProxyTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A simple calculator tool for testing

.. dropdown:: mcp_mock_calculator tool specification

   **Tool Information:**

   * **Name**: ``mcp_mock_calculator``
   * **Type**: ``MCPProxyTool``
   * **Description**: A simple calculator tool for testing

   **Parameters:**

   * ``operation`` (string) (required)
     The mathematical operation to perform

   * ``a`` (number) (required)
     First number

   * ``b`` (number) (required)
     Second number

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "mcp_mock_calculator",
          "arguments": {
              "operation": "example_value",
              "a": "example_value",
              "b": "example_value"
          }
      }
      result = tu.run(query)


**mcp_mock_greeter** (Type: MCPProxyTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A simple greeting tool

.. dropdown:: mcp_mock_greeter tool specification

   **Tool Information:**

   * **Name**: ``mcp_mock_greeter``
   * **Type**: ``MCPProxyTool``
   * **Description**: A simple greeting tool

   **Parameters:**

   * ``name`` (string) (required)
     Name to greet

   * ``language`` (string) (required)
     Language for greeting

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "mcp_mock_greeter",
          "arguments": {
              "name": "example_value",
              "language": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
