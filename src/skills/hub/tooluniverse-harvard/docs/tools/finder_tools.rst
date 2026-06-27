Finder Tools
============

**Configuration File**: ``finder_tools.json``
**Tool Type**: Local
**Tools Count**: 4

This page contains all tools defined in the ``finder_tools.json`` configuration file.

Available Tools
---------------

**Tool_Finder** (Type: ToolFinderEmbedding)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve related tools from the toolbox based on the provided description, advanced version with ...

.. dropdown:: Tool_Finder tool specification

   **Tool Information:**

   * **Name**: ``Tool_Finder``
   * **Type**: ``ToolFinderEmbedding``
   * **Description**: Retrieve related tools from the toolbox based on the provided description, advanced version with more functionality.

   **Parameters:**

   * ``description`` (string) (required)
     The description of the tool capability required.

   * ``limit`` (integer) (required)
     The number of tools to retrieve

   * ``picked_tool_names`` (array) (optional)
     Pre-selected tool names to process. If provided, tool selection will skip these tools.

   * ``return_call_result`` (boolean) (optional)
     Whether to return both prompts and tool names. If false, returns only tool prompts.

   * ``categories`` (array) (optional)
     Optional list of tool categories to filter by

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Tool_Finder",
          "arguments": {
              "description": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


**Tool_Finder_Keyword** (Type: ToolFinderKeyword)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Simple keyword-based tool finder for discovering relevant tools using text matching

.. dropdown:: Tool_Finder_Keyword tool specification

   **Tool Information:**

   * **Name**: ``Tool_Finder_Keyword``
   * **Type**: ``ToolFinderKeyword``
   * **Description**: Simple keyword-based tool finder for discovering relevant tools using text matching

   **Parameters:**

   * ``description`` (string) (required)
     The description of the tool capability required.

   * ``limit`` (integer) (required)
     The number of tools to retrieve

   * ``picked_tool_names`` (array) (optional)
     Pre-selected tool names to process. If provided, tool selection will skip these tools.

   * ``return_call_result`` (boolean) (optional)
     Whether to return both prompts and tool names. If false, returns only tool prompts.

   * ``categories`` (array) (optional)
     Optional list of tool categories to filter by

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Tool_Finder_Keyword",
          "arguments": {
              "description": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


**Tool_Finder_LLM** (Type: ToolFinderLLM)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LLM-based tool finder that uses natural language processing to intelligently select relevant tool...

.. dropdown:: Tool_Finder_LLM tool specification

   **Tool Information:**

   * **Name**: ``Tool_Finder_LLM``
   * **Type**: ``ToolFinderLLM``
   * **Description**: LLM-based tool finder that uses natural language processing to intelligently select relevant tools based on user queries. This tool analyzes all available tool descriptions and uses an LLM to determine which tools would be most helpful for a given task or question.

   **Parameters:**

   * ``description`` (string) (required)
     The description of the tool capability required.

   * ``limit`` (integer) (required)
     The number of tools to retrieve

   * ``picked_tool_names`` (array) (optional)
     Pre-selected tool names to process. If provided, tool selection will skip these tools.

   * ``return_call_result`` (boolean) (optional)
     Whether to return both prompts and tool names. If false, returns only tool prompts.

   * ``categories`` (array) (optional)
     Optional list of tool categories to filter by

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Tool_Finder_LLM",
          "arguments": {
              "description": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


**Tool_RAG** (Type: ToolFinderEmbedding)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve related tools from the toolbox based on the provided description

.. dropdown:: Tool_RAG tool specification

   **Tool Information:**

   * **Name**: ``Tool_RAG``
   * **Type**: ``ToolFinderEmbedding``
   * **Description**: Retrieve related tools from the toolbox based on the provided description

   **Parameters:**

   * ``description`` (string) (required)
     The description of the tool capability required.

   * ``limit`` (integer) (required)
     The number of tools to retrieve

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Tool_RAG",
          "arguments": {
              "description": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
