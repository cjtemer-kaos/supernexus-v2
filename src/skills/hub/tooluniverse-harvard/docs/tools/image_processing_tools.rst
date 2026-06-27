Image Processing Tools
======================

**Configuration File**: ``packages/image_processing_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``image_processing_tools.json`` configuration file.

Available Tools
---------------

**get_albumentations_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the albumentations package. Fast image augmentation library

.. dropdown:: get_albumentations_info tool specification

   **Tool Information:**

   * **Name**: ``get_albumentations_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the albumentations package. Fast image augmentation library

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_albumentations_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_imageio_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the imageio package. Python library for reading and writing image data

.. dropdown:: get_imageio_info tool specification

   **Tool Information:**

   * **Name**: ``get_imageio_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the imageio package. Python library for reading and writing image data

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_imageio_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_pillow_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the pillow package. Python Imaging Library fork

.. dropdown:: get_pillow_info tool specification

   **Tool Information:**

   * **Name**: ``get_pillow_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the pillow package. Python Imaging Library fork

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_pillow_info",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
