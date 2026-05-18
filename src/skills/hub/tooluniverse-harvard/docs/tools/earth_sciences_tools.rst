Earth Sciences Tools
====================

**Configuration File**: ``packages/earth_sciences_tools.json``
**Tool Type**: Local
**Tools Count**: 6

This page contains all tools defined in the ``earth_sciences_tools.json`` configuration file.

Available Tools
---------------

**get_cartopy_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the cartopy package. Cartographic projections and geospatial data processing

.. dropdown:: get_cartopy_info tool specification

   **Tool Information:**

   * **Name**: ``get_cartopy_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the cartopy package. Cartographic projections and geospatial data processing

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_cartopy_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_cftime_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the cftime package. Time-handling functionality from netcdf4-python

.. dropdown:: get_cftime_info tool specification

   **Tool Information:**

   * **Name**: ``get_cftime_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the cftime package. Time-handling functionality from netcdf4-python

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_cftime_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_geopandas_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the geopandas package. Geospatial data manipulation and analysis

.. dropdown:: get_geopandas_info tool specification

   **Tool Information:**

   * **Name**: ``get_geopandas_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the geopandas package. Geospatial data manipulation and analysis

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_geopandas_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_netcdf4_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the netcdf4 package. Python interface to netCDF C library

.. dropdown:: get_netcdf4_info tool specification

   **Tool Information:**

   * **Name**: ``get_netcdf4_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the netcdf4 package. Python interface to netCDF C library

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_netcdf4_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_rasterio_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the rasterio package. Access to geospatial raster data

.. dropdown:: get_rasterio_info tool specification

   **Tool Information:**

   * **Name**: ``get_rasterio_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the rasterio package. Access to geospatial raster data

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_rasterio_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_xesmf_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the xesmf package. Universal regridder for geospatial data

.. dropdown:: get_xesmf_info tool specification

   **Tool Information:**

   * **Name**: ``get_xesmf_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the xesmf package. Universal regridder for geospatial data

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_xesmf_info",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
