Neuroscience Tools
==================

**Configuration File**: ``packages/neuroscience_tools.json``
**Tool Type**: Local
**Tools Count**: 5

This page contains all tools defined in the ``neuroscience_tools.json`` configuration file.

Available Tools
---------------

**get_brian2_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the brian2 package. Spiking neural network simulator

.. dropdown:: get_brian2_info tool specification

   **Tool Information:**

   * **Name**: ``get_brian2_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the brian2 package. Spiking neural network simulator

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_brian2_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_elephant_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the elephant package. Electrophysiology analysis toolkit

.. dropdown:: get_elephant_info tool specification

   **Tool Information:**

   * **Name**: ``get_elephant_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the elephant package. Electrophysiology analysis toolkit

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_elephant_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_mne_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the mne package. MEG and EEG data analysis

.. dropdown:: get_mne_info tool specification

   **Tool Information:**

   * **Name**: ``get_mne_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the mne package. MEG and EEG data analysis

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_mne_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_neo_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the neo package. Representation of electrophysiology data

.. dropdown:: get_neo_info tool specification

   **Tool Information:**

   * **Name**: ``get_neo_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the neo package. Representation of electrophysiology data

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_neo_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_nilearn_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the nilearn package. Machine learning for neuroimaging

.. dropdown:: get_nilearn_info tool specification

   **Tool Information:**

   * **Name**: ``get_nilearn_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the nilearn package. Machine learning for neuroimaging

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_nilearn_info",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
