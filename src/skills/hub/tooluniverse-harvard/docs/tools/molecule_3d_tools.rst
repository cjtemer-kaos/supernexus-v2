Molecule 3D Tools
=================

**Configuration File**: ``molecule_3d_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``molecule_3d_tools.json`` configuration file.

Available Tools
---------------

**visualize_molecule_3d** (Type: Molecule3DTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Visualize 3D molecular structures using RDKit and py3Dmol. Supports SMILES, MOL files, SDF conten...

.. dropdown:: visualize_molecule_3d tool specification

   **Tool Information:**

   * **Name**: ``visualize_molecule_3d``
   * **Type**: ``Molecule3DTool``
   * **Description**: Visualize 3D molecular structures using RDKit and py3Dmol. Supports SMILES, MOL files, SDF content, and various visualization styles with interactive 3D viewing capabilities.

   **Parameters:**

   * ``smiles`` (string) (required)
     SMILES string representation of the molecule

   * ``mol_content`` (string) (required)
     MOL file content as string

   * ``sdf_content`` (string) (required)
     SDF file content as string

   * ``style`` (string) (optional)
     Visualization style

   * ``color_scheme`` (string) (optional)
     Color scheme for the molecule

   * ``width`` (integer) (optional)
     Width of the visualization in pixels

   * ``height`` (integer) (optional)
     Height of the visualization in pixels

   * ``show_hydrogens`` (boolean) (optional)
     Whether to show hydrogen atoms

   * ``show_surface`` (boolean) (optional)
     Whether to show molecular surface

   * ``generate_conformers`` (boolean) (optional)
     Whether to generate multiple conformers

   * ``conformer_count`` (integer) (optional)
     Number of conformers to generate

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "visualize_molecule_3d",
          "arguments": {
              "smiles": "example_value",
              "mol_content": "example_value",
              "sdf_content": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
