Unified Guideline Tools
=======================

**Configuration File**: ``unified_guideline_tools.json``
**Tool Type**: Local
**Tools Count**: 10

This page contains all tools defined in the ``unified_guideline_tools.json`` configuration file.

Available Tools
---------------

**CMA_Guidelines_Search** (Type: CMAGuidelinesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Canadian Medical Association (CMA) Infobase guidelines. Contains over 1200 evidence-based ...

.. dropdown:: CMA_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``CMA_Guidelines_Search``
   * **Type**: ``CMAGuidelinesTool``
   * **Description**: Search Canadian Medical Association (CMA) Infobase guidelines. Contains over 1200 evidence-based clinical practice guidelines developed or endorsed by Canadian healthcare organizations.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition, treatment, or clinical topic to search for in CMA guidelines (e.g., 'diabetes management', 'hypertension treatment', 'cancer screening')

   * ``limit`` (integer) (required)
     Maximum number of guidelines to return (default: 10)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "CMA_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


**EuropePMC_Guidelines_Search** (Type: EuropePMCGuidelinesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Europe PMC for clinical guidelines and evidence-based recommendations. Europe PMC provides...

.. dropdown:: EuropePMC_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``EuropePMC_Guidelines_Search``
   * **Type**: ``EuropePMCGuidelinesTool``
   * **Description**: Search Europe PMC for clinical guidelines and evidence-based recommendations. Europe PMC provides free access to a comprehensive archive of life sciences literature, including clinical practice guidelines from international sources.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition, treatment, or clinical topic to search for (e.g., 'diabetes', 'cardiovascular disease', 'mental health')

   * ``limit`` (integer) (required)
     Maximum number of guidelines to return (default: 10)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "EuropePMC_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


**GIN_Guidelines_Search** (Type: GINGuidelinesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Guidelines International Network (GIN) guidelines database. GIN maintains the world's larg...

.. dropdown:: GIN_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``GIN_Guidelines_Search``
   * **Type**: ``GINGuidelinesTool``
   * **Description**: Search Guidelines International Network (GIN) guidelines database. GIN maintains the world's largest database of clinical guidelines with over 6400 guidelines from various organizations worldwide.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition, treatment, or clinical topic to search for in GIN guidelines (e.g., 'diabetes management', 'hypertension treatment', 'cancer screening')

   * ``limit`` (integer) (required)
     Maximum number of guidelines to return (default: 10)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GIN_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


**NICE_Clinical_Guidelines_Search** (Type: NICEWebScrapingTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search NICE (National Institute for Health and Care Excellence) clinical guidelines and evidence-...

.. dropdown:: NICE_Clinical_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``NICE_Clinical_Guidelines_Search``
   * **Type**: ``NICEWebScrapingTool``
   * **Description**: Search NICE (National Institute for Health and Care Excellence) clinical guidelines and evidence-based recommendations. Provides access to official NICE guidelines covering diagnosis, treatment, and care pathways for various medical conditions.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition, treatment, or clinical topic to search for in NICE guidelines (e.g., 'diabetes', 'hypertension', 'cancer screening')

   * ``limit`` (integer) (required)
     Maximum number of clinical guidelines to return (default: 10)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "NICE_Clinical_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


**NICE_Guideline_Full_Text** (Type: NICEGuidelineFullTextTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch complete full text content from a NICE clinical guideline page. Takes a NICE guideline URL ...

.. dropdown:: NICE_Guideline_Full_Text tool specification

   **Tool Information:**

   * **Name**: ``NICE_Guideline_Full_Text``
   * **Type**: ``NICEGuidelineFullTextTool``
   * **Description**: Fetch complete full text content from a NICE clinical guideline page. Takes a NICE guideline URL and extracts all sections, recommendations, and complete guideline text. Use this after finding a guideline with NICE_Clinical_Guidelines_Search to get the full content.

   **Parameters:**

   * ``url`` (string) (required)
     Full URL of the NICE guideline page (e.g., 'https://www.nice.org.uk/guidance/ng28'). Must be a valid NICE guideline URL.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "NICE_Guideline_Full_Text",
          "arguments": {
              "url": "example_value"
          }
      }
      result = tu.run(query)


**OpenAlex_Guidelines_Search** (Type: OpenAlexGuidelinesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for clinical practice guidelines using OpenAlex scholarly database. Provides access to a c...

.. dropdown:: OpenAlex_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``OpenAlex_Guidelines_Search``
   * **Type**: ``OpenAlexGuidelinesTool``
   * **Description**: Search for clinical practice guidelines using OpenAlex scholarly database. Provides access to a comprehensive collection of guidelines from various sources worldwide, with citation metrics and institutional affiliations.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition or clinical topic to search for guidelines (e.g., 'diabetes management', 'hypertension treatment', 'cancer screening')

   * ``limit`` (integer) (required)
     Maximum number of guidelines to return (default: 10)

   * ``year_from`` (integer) (required)
     Filter for guidelines published from this year onwards (optional)

   * ``year_to`` (integer) (required)
     Filter for guidelines published up to this year (optional)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenAlex_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10,
              "year_from": 10,
              "year_to": 10
          }
      }
      result = tu.run(query)


**PubMed_Guidelines_Search** (Type: PubMedGuidelinesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search PubMed for peer-reviewed clinical practice guidelines using NCBI E-utilities. Filters resu...

.. dropdown:: PubMed_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``PubMed_Guidelines_Search``
   * **Type**: ``PubMedGuidelinesTool``
   * **Description**: Search PubMed for peer-reviewed clinical practice guidelines using NCBI E-utilities. Filters results specifically for guideline and practice guideline publication types. Provides access to high-quality, evidence-based clinical guidelines from medical journals worldwide.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition, treatment, or clinical topic to search for (e.g., 'diabetes', 'hypertension management', 'cancer treatment')

   * ``limit`` (integer) (required)
     Maximum number of guidelines to return (default: 10)

   * ``api_key`` (string) (required)
     Optional NCBI API key for higher rate limits. Get your free key at https://www.ncbi.nlm.nih.gov/account/

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PubMed_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10,
              "api_key": "example_value"
          }
      }
      result = tu.run(query)


**TRIP_Database_Guidelines_Search** (Type: TRIPDatabaseTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search TRIP Database (Turning Research into Practice) for evidence-based clinical guidelines. TRI...

.. dropdown:: TRIP_Database_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``TRIP_Database_Guidelines_Search``
   * **Type**: ``TRIPDatabaseTool``
   * **Description**: Search TRIP Database (Turning Research into Practice) for evidence-based clinical guidelines. TRIP is a specialized clinical search engine that focuses on high-quality evidence-based content, particularly clinical guidelines from reputable sources worldwide.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition, treatment, or clinical question (e.g., 'diabetes management', 'stroke prevention', 'antibiotic therapy')

   * ``limit`` (integer) (required)
     Maximum number of guidelines to return (default: 10)

   * ``search_type`` (string) (required)
     Type of content to search for (default: 'guideline'). Options include 'guideline', 'systematic-review', 'evidence-based-synopses'

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "TRIP_Database_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10,
              "search_type": "example_value"
          }
      }
      result = tu.run(query)


**WHO_Guideline_Full_Text** (Type: WHOGuidelineFullTextTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch full text content from a WHO (World Health Organization) guideline publication page. Extrac...

.. dropdown:: WHO_Guideline_Full_Text tool specification

   **Tool Information:**

   * **Name**: ``WHO_Guideline_Full_Text``
   * **Type**: ``WHOGuidelineFullTextTool``
   * **Description**: Fetch full text content from a WHO (World Health Organization) guideline publication page. Extracts available web content and finds PDF download links. Use this after finding a guideline with WHO_Guidelines_Search to get the full content or PDF link.

   **Parameters:**

   * ``url`` (string) (required)
     Full URL of the WHO publication page (e.g., 'https://www.who.int/publications/i/item/9789240113879'). Must be a valid WHO publication URL.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "WHO_Guideline_Full_Text",
          "arguments": {
              "url": "example_value"
          }
      }
      result = tu.run(query)


**WHO_Guidelines_Search** (Type: WHOGuidelinesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search WHO (World Health Organization) official clinical guidelines and health recommendations. P...

.. dropdown:: WHO_Guidelines_Search tool specification

   **Tool Information:**

   * **Name**: ``WHO_Guidelines_Search``
   * **Type**: ``WHOGuidelinesTool``
   * **Description**: Search WHO (World Health Organization) official clinical guidelines and health recommendations. Provides access to authoritative global health guidelines published by WHO.

   **Parameters:**

   * ``query`` (string) (required)
     Medical condition, disease, or health topic to search for in WHO guidelines (e.g., 'malaria', 'HIV', 'diabetes', 'tuberculosis')

   * ``limit`` (integer) (required)
     Maximum number of guidelines to return (default: 10)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "WHO_Guidelines_Search",
          "arguments": {
              "query": "example_value",
              "limit": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
