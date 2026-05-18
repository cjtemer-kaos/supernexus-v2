Clinicaltrials Gov Tools
========================

**Configuration File**: ``clinicaltrials_gov_tools.json``
**Tool Type**: Local
**Tools Count**: 10

This page contains all tools defined in the ``clinicaltrials_gov_tools.json`` configuration file.

Available Tools
---------------

**extract_clinical_trial_adverse_events** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extracts detailed adverse event results from clinicaltrials.gov, using their NCT IDs.

.. dropdown:: extract_clinical_trial_adverse_events tool specification

   **Tool Information:**

   * **Name**: ``extract_clinical_trial_adverse_events``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Extracts detailed adverse event results from clinicaltrials.gov, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``organ_systems`` (array) (optional)
     List of organs or organ systems to filter adverse events (see enum for exact text). Adverse events will be matched only if the input exactly matches their terms (case agnostic). If not specified, all adverse events will be returned. By default, all adverse events will be returned.

   * ``adverse_event_type`` (string) (optional)
     Type of adverse events to extract. Options are 'serious' (serious adverse events only), 'other' (non-serious adverse events only), 'all' (all adverse events), or specific event names such as 'nausea', 'neutropenia', 'epilepsy' (from MedDRA). For specific event names, adverse events will be matched as long as the input partially matches their terms (case agnostic). Querying for specific adverse event names is recommended as there are typically many adverse events logged. If querying for specific event names does not return any results, this parameter should be set to 'serious' for sanity check. By default, the value is set to 'serious', i.e. the tool will extract all serious adverse events.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "extract_clinical_trial_adverse_events",
          "arguments": {
              "nct_ids": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**extract_clinical_trial_outcomes** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extracts detailed trial outcome results (e.g., overall survival months, p-values, etc.) from clin...

.. dropdown:: extract_clinical_trial_outcomes tool specification

   **Tool Information:**

   * **Name**: ``extract_clinical_trial_outcomes``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Extracts detailed trial outcome results (e.g., overall survival months, p-values, etc.) from clinicaltrials.gov, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``outcome_measure`` (string) (optional)
     Outcome measure to extract. Example values include 'primary' (primary outcomes only), 'secondary' (secondary outcomes only), 'all' (all outcomes), or specific measure names such as 'survival', 'overall survival'. For specific measure names, outcome measures will be matched as long as the input partially matches their titles or descriptions (case agnostic). Querying for specific measure names is recommended after getting an overview of outcome measures ('primary'). If querying for specific measure names does not return any results, this parameter should be set to 'primary' for sanity check. By default, the value is set to 'primary', i.e. the tool will extract all primary outcome results.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "extract_clinical_trial_outcomes",
          "arguments": {
              "nct_ids": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**get_clinical_trial_conditions_and_interventions** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves the list of conditions or diseases and the interventions and arm groups that the clinic...

.. dropdown:: get_clinical_trial_conditions_and_interventions tool specification

   **Tool Information:**

   * **Name**: ``get_clinical_trial_conditions_and_interventions``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Retrieves the list of conditions or diseases and the interventions and arm groups that the clinical trials are focused on, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``condition_and_intervention`` (string) (required)
     Placeholder.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_clinical_trial_conditions_and_interventions",
          "arguments": {
              "nct_ids": ["item1", "item2"],
              "condition_and_intervention": "example_value"
          }
      }
      result = tu.run(query)


**get_clinical_trial_descriptions** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves detailed identification information for trials, including titles, phases, and descripti...

.. dropdown:: get_clinical_trial_descriptions tool specification

   **Tool Information:**

   * **Name**: ``get_clinical_trial_descriptions``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Retrieves detailed identification information for trials, including titles, phases, and descriptions, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``description_type`` (string) (required)
     Type of information to retrieve. Options are 'brief' for brief descriptions or 'full' for full descriptions.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_clinical_trial_descriptions",
          "arguments": {
              "nct_ids": ["item1", "item2"],
              "description_type": "example_value"
          }
      }
      result = tu.run(query)


**get_clinical_trial_eligibility_criteria** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves the eligibility criteria for the clinical trials, using their NCT IDs.

.. dropdown:: get_clinical_trial_eligibility_criteria tool specification

   **Tool Information:**

   * **Name**: ``get_clinical_trial_eligibility_criteria``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Retrieves the eligibility criteria for the clinical trials, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``eligibility_criteria`` (string) (required)
     Placeholder.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_clinical_trial_eligibility_criteria",
          "arguments": {
              "nct_ids": ["item1", "item2"],
              "eligibility_criteria": "example_value"
          }
      }
      result = tu.run(query)


**get_clinical_trial_locations** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves the locations where the clinical trials are being conducted, using their NCT IDs.

.. dropdown:: get_clinical_trial_locations tool specification

   **Tool Information:**

   * **Name**: ``get_clinical_trial_locations``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Retrieves the locations where the clinical trials are being conducted, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``location`` (string) (required)
     Placeholder.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_clinical_trial_locations",
          "arguments": {
              "nct_ids": ["item1", "item2"],
              "location": "example_value"
          }
      }
      result = tu.run(query)


**get_clinical_trial_outcome_measures** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves the outcome measures for the clinical trials, using their NCT IDs.

.. dropdown:: get_clinical_trial_outcome_measures tool specification

   **Tool Information:**

   * **Name**: ``get_clinical_trial_outcome_measures``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Retrieves the outcome measures for the clinical trials, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``outcome_measures`` (string) (optional)
     Decides whether to retrieve primary, secondary, or all outcome measures. Options are 'primary', 'secondary', or 'all'. Default is 'primary'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_clinical_trial_outcome_measures",
          "arguments": {
              "nct_ids": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**get_clinical_trial_references** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves the references (if any) for the clinical trials, using their NCT IDs.

.. dropdown:: get_clinical_trial_references tool specification

   **Tool Information:**

   * **Name**: ``get_clinical_trial_references``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Retrieves the references (if any) for the clinical trials, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``references`` (string) (required)
     Placeholder.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_clinical_trial_references",
          "arguments": {
              "nct_ids": ["item1", "item2"],
              "references": "example_value"
          }
      }
      result = tu.run(query)


**get_clinical_trial_status_and_dates** (Type: ClinicalTrialsDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves trial status and start and completion dates, using their NCT IDs.

.. dropdown:: get_clinical_trial_status_and_dates tool specification

   **Tool Information:**

   * **Name**: ``get_clinical_trial_status_and_dates``
   * **Type**: ``ClinicalTrialsDetailsTool``
   * **Description**: Retrieves trial status and start and completion dates, using their NCT IDs.

   **Parameters:**

   * ``nct_ids`` (array) (required)
     List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).

   * ``status_and_date`` (string) (required)
     Placeholder.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_clinical_trial_status_and_dates",
          "arguments": {
              "nct_ids": ["item1", "item2"],
              "status_and_date": "example_value"
          }
      }
      result = tu.run(query)


**search_clinical_trials** (Type: ClinicalTrialsSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for clinical trials registered on clinicaltrials.gov based on title, conditions, intervent...

.. dropdown:: search_clinical_trials tool specification

   **Tool Information:**

   * **Name**: ``search_clinical_trials``
   * **Type**: ``ClinicalTrialsSearchTool``
   * **Description**: Search for clinical trials registered on clinicaltrials.gov based on title, conditions, interventions, outcome measures, and status. Returns a paginated list of studies, containing the NCT ID and description of each trial. You can then take the NCT IDs and use 'get_clinical_trials_*' tools to get detailed information about specific protocol fields for specific studies, or 'extract_clinical_trials_efficacy/safety' tools to get efficacy or adverse events results from specific studies. If you wish to see the next page of results, you can use the 'nextPageToken' value from the previous output of this tool and input it as the 'pageToken' parameter in the next query. Note that currently the search is limited to trials beyond phase 1.

   **Parameters:**

   * ``condition`` (string) (optional)
     Query for condition or disease using Essie expression syntax (e.g., 'lung cancer', '(head OR neck) AND pain AND NOT "back pain"'). 

   * ``intervention`` (string) (optional)
     Query for intervention/treatment using Essie expression syntax (e.g., 'chemotherapy', 'immunotherapy', 'olaparib', 'combination therapy').

   * ``query_term`` (string) (required)
     Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]', 'Phase II'). Can be used to search for all other protocol fields, including but not limited to title, outcome measures, status, phase, location, etc.

   * ``pageSize`` (integer) (optional)
     Maximum number of studies to return per page (default 10, max 1000).

   * ``pageToken`` (string) (optional)
     Token to retrieve the next page of results, obtained from the 'nextPageToken' field of the previous response. Do not specify it for first page. When you make an initial request to the API which supports pagination, the response will include a nextPageToken. This token can then be used as a parameter in the subsequent API request to retrieve the next set of data.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "search_clinical_trials",
          "arguments": {
              "query_term": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
