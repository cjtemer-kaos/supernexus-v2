Special Tools
=============

**Configuration File**: ``special_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``special_tools.json`` configuration file.

Available Tools
---------------

**CallAgent** (Type: SpecialTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Give a solution plan to the agent and let it solve the problem. Solution plan should reflect a di...

.. dropdown:: CallAgent tool specification

   **Tool Information:**

   * **Name**: ``CallAgent``
   * **Type**: ``SpecialTool``
   * **Description**: Give a solution plan to the agent and let it solve the problem. Solution plan should reflect a distinct method, approach, or viewpoint to solve the given question. Call these function multiple times, and each solution plan should start with different aspects of the question, for example, genes, phenotypes, diseases, or drugs, etc. The CallAgent will achieve the task based on the plan, so only give the plan instead of unverified information.

   **Parameters:**

   * ``solution`` (string) (required)
     A feasible and concise solution plan that address the question.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "CallAgent",
          "arguments": {
              "solution": "example_value"
          }
      }
      result = tu.run(query)


**Finish** (Type: SpecialTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Indicate the end of multi-step reasoning.

.. dropdown:: Finish tool specification

   **Tool Information:**

   * **Name**: ``Finish``
   * **Type**: ``SpecialTool``
   * **Description**: Indicate the end of multi-step reasoning.

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Finish",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
