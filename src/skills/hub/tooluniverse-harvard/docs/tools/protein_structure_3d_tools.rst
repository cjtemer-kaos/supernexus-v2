Protein Structure 3D Tools
==========================

**Configuration File**: ``protein_structure_3d_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``protein_structure_3d_tools.json`` configuration file.

Available Tools
---------------

**visualize_protein_structure_3d** (Type: ProteinStructure3DTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Visualize 3D protein structures using py3Dmol. Supports PDB IDs, PDB file content, and various vi...

.. dropdown:: visualize_protein_structure_3d tool specification

   **Tool Information:**

   * **Name**: ``visualize_protein_structure_3d``
   * **Type**: ``ProteinStructure3DTool``
   * **Description**: Visualize 3D protein structures using py3Dmol. Supports PDB IDs, PDB file content, and various visualization styles including cartoon, surface, and stick representations.

   **Parameters:**

   * ``pdb_id`` (string) (required)
     PDB identifier (e.g., '1CRN', '7CGO'). Either pdb_id or pdb_content must be provided.

   * ``pdb_content`` (string) (required)
     Raw PDB file content as string. Either pdb_id or pdb_content must be provided.

   * ``style`` (string) (optional)
     Visualization style

   * ``color_scheme`` (string) (optional)
     Color scheme for the structure

   * ``width`` (integer) (optional)
     Width of the visualization in pixels

   * ``height`` (integer) (optional)
     Height of the visualization in pixels

   * ``show_sidechains`` (boolean) (optional)
     Whether to show sidechain atoms

   * ``show_surface`` (boolean) (optional)
     Whether to show molecular surface

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "visualize_protein_structure_3d",
          "arguments": {
              "pdb_id": "example_value",
              "pdb_content": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
