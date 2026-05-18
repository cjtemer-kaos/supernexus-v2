Molecule 2D Tools
=================

**Configuration File**: ``molecule_2d_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``molecule_2d_tools.json`` configuration file.

Available Tools
---------------

**visualize_molecule_2d** (Type: Molecule2DTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Visualize 2D molecular structures using RDKit. Supports SMILES, InChI, molecule names, and variou...

.. dropdown:: visualize_molecule_2d tool specification

   **Tool Information:**

   * **Name**: ``visualize_molecule_2d``
   * **Type**: ``Molecule2DTool``
   * **Description**: Visualize 2D molecular structures using RDKit. Supports SMILES, InChI, molecule names, and various output formats including PNG, SVG, and interactive HTML.

   **Parameters:**

   * ``smiles`` (string) (required)
     SMILES string representation of the molecule

   * ``inchi`` (string) (required)
     InChI string representation of the molecule

   * ``molecule_name`` (string) (required)
     Common name of the molecule (will be resolved to SMILES via PubChem)

   * ``width`` (integer) (optional)
     Width of the visualization in pixels

   * ``height`` (integer) (optional)
     Height of the visualization in pixels

   * ``output_format`` (string) (optional)
     Output format

   * ``show_atom_numbers`` (boolean) (optional)
     Whether to show atom numbers

   * ``show_bond_numbers`` (boolean) (optional)
     Whether to show bond numbers

   * ``include_stereo`` (boolean) (optional)
     Whether to include stereochemistry information

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "visualize_molecule_2d",
          "arguments": {
              "smiles": "example_value",
              "inchi": "example_value",
              "molecule_name": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
