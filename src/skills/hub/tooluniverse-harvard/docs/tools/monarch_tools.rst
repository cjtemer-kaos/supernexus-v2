Monarch Tools
=============

**Configuration File**: ``monarch_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``monarch_tools.json`` configuration file.

Available Tools
---------------

**get_HPO_ID_by_phenotype** (Type: Monarch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the HPO ID of a phenotype or symptom.

.. dropdown:: get_HPO_ID_by_phenotype tool specification

   **Tool Information:**

   * **Name**: ``get_HPO_ID_by_phenotype``
   * **Type**: ``Monarch``
   * **Description**: Retrieve the HPO ID of a phenotype or symptom.

   **Parameters:**

   * ``query`` (string) (required)
     One query phenotype or symptom.

   * ``limit`` (integer) (optional)
     Number of entries to fetch.

   * ``offset`` (integer) (optional)
     Number of initial entries to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_HPO_ID_by_phenotype",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


**get_joint_associated_diseases_by_HPO_ID_list** (Type: MonarchDiseasesForMultiplePheno)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve diseases associated with a list of phenotypes or symptoms by a list of HPO IDs.

.. dropdown:: get_joint_associated_diseases_by_HPO_ID_list tool specification

   **Tool Information:**

   * **Name**: ``get_joint_associated_diseases_by_HPO_ID_list``
   * **Type**: ``MonarchDiseasesForMultiplePheno``
   * **Description**: Retrieve diseases associated with a list of phenotypes or symptoms by a list of HPO IDs.

   **Parameters:**

   * ``HPO_ID_list`` (array) (required)
     List of phenotypes or symptoms

   * ``limit`` (integer) (optional)
     Number of entries to fetch.

   * ``offset`` (integer) (optional)
     Number of initial entries to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_joint_associated_diseases_by_HPO_ID_list",
          "arguments": {
              "HPO_ID_list": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**get_phenotype_by_HPO_ID** (Type: Monarch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a phenotype or symptom by its HPO ID.

.. dropdown:: get_phenotype_by_HPO_ID tool specification

   **Tool Information:**

   * **Name**: ``get_phenotype_by_HPO_ID``
   * **Type**: ``Monarch``
   * **Description**: Retrieve a phenotype or symptom by its HPO ID.

   **Parameters:**

   * ``id`` (string) (required)
     The HPO ID of the phenotype or symptom.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_phenotype_by_HPO_ID",
          "arguments": {
              "id": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
