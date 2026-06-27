Admetai Tools
=============

**Configuration File**: ``admetai_tools.json``
**Tool Type**: Local
**Tools Count**: 9

This page contains all tools defined in the ``admetai_tools.json`` configuration file.

Available Tools
---------------

**ADMETAI_predict_BBB_penetrance** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts blood-brain barrier (BBB) penetrance for a given list of molecules in SMILES format.

.. dropdown:: ADMETAI_predict_BBB_penetrance tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_BBB_penetrance``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts blood-brain barrier (BBB) penetrance for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_BBB_penetrance",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_CYP_interactions** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts CYP enzyme interactions for a given list of molecules in SMILES format.

.. dropdown:: ADMETAI_predict_CYP_interactions tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_CYP_interactions``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts CYP enzyme interactions for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_CYP_interactions",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_bioavailability** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts bioavailability endpoints (Bioavailability_Ma, HIA_Hou, PAMPA_NCATS, Caco2_Wang, Pgp_Bro...

.. dropdown:: ADMETAI_predict_bioavailability tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_bioavailability``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts bioavailability endpoints (Bioavailability_Ma, HIA_Hou, PAMPA_NCATS, Caco2_Wang, Pgp_Broccatelli) for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_bioavailability",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_clearance_distribution** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts clearance and distribution endpoints (Clearance_Hepatocyte_AZ, Clearance_Microsome_AZ, H...

.. dropdown:: ADMETAI_predict_clearance_distribution tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_clearance_distribution``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts clearance and distribution endpoints (Clearance_Hepatocyte_AZ, Clearance_Microsome_AZ, Half_Life_Obach, VDss_Lombardo, PPBR_AZ) for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_clearance_distribution",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_nuclear_receptor_activity** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts nuclear receptor activity endpoints (NR-AR-LBD, NR-AR, NR-AhR, NR-Aromatase, NR-ER-LBD, ...

.. dropdown:: ADMETAI_predict_nuclear_receptor_activity tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_nuclear_receptor_activity``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts nuclear receptor activity endpoints (NR-AR-LBD, NR-AR, NR-AhR, NR-Aromatase, NR-ER-LBD, NR-ER, NR-PPAR-gamma) for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_nuclear_receptor_activity",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_physicochemical_properties** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts physicochemical properties (molecular weight, logP, hydrogen bond acceptors/donors, Lipi...

.. dropdown:: ADMETAI_predict_physicochemical_properties tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_physicochemical_properties``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts physicochemical properties (molecular weight, logP, hydrogen bond acceptors/donors, Lipinski, QED, stereo centers, TPSA) for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_physicochemical_properties",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_solubility_lipophilicity_hydration** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts solubility, lipophilicity, and hydration endpoints (Solubility_AqSolDB, Lipophilicity_As...

.. dropdown:: ADMETAI_predict_solubility_lipophilicity_hydration tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_solubility_lipophilicity_hydration``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts solubility, lipophilicity, and hydration endpoints (Solubility_AqSolDB, Lipophilicity_AstraZeneca, HydrationFreeEnergy_FreeSolv) for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_solubility_lipophilicity_hydration",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_stress_response** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts stress response endpoints (SR-ARE, SR-ATAD5, SR-HSE, SR-MMP, SR-p53) for a given list of...

.. dropdown:: ADMETAI_predict_stress_response tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_stress_response``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts stress response endpoints (SR-ARE, SR-ATAD5, SR-HSE, SR-MMP, SR-p53) for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_stress_response",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ADMETAI_predict_toxicity** (Type: ADMETAITool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Predicts toxicity endpoints (AMES, Carcinogens_Lagunin, ClinTox, DILI, LD50_Zhu, Skin_Reaction, h...

.. dropdown:: ADMETAI_predict_toxicity tool specification

   **Tool Information:**

   * **Name**: ``ADMETAI_predict_toxicity``
   * **Type**: ``ADMETAITool``
   * **Description**: Predicts toxicity endpoints (AMES, Carcinogens_Lagunin, ClinTox, DILI, LD50_Zhu, Skin_Reaction, hERG) for a given list of molecules in SMILES format.

   **Parameters:**

   * ``smiles`` (array) (required)
     The list of SMILES strings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ADMETAI_predict_toxicity",
          "arguments": {
              "smiles": ["item1", "item2"]
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
