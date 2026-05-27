# === openfda_test_all_tools.py ===

from tooluniverse import ToolUniverse

# Step 1: Initialize tool universe
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define all test queries for all tools
test_queries = [
    # # ====== Tests for FAERS_count_reactions_by_drug_event ======
    # {"name": "FAERS_count_reactions_by_drug_event", "arguments": {"medicinalproduct": "LIPITOR"}},
    # {"name": "FAERS_count_reactions_by_drug_event", "arguments": {"medicinalproduct": "LIPITOR", "patient.patientsex": "Male", "serious": "Serious"}},
    # {"name": "FAERS_count_reactions_by_drug_event", "arguments": {"medicinalproduct": "ASPIRIN", "patient.patientagegroup": "Adult"}},
    # {"name": "FAERS_count_reactions_by_drug_event", "arguments": {"medicinalproduct": "ADVIL", "patient.patientsex": "Female", "patient.patientagegroup": "Elderly", "occurcountry": "US", "serious": "Non-serious"}},
    # {"name": "FAERS_count_reactions_by_drug_event", "arguments": {"medicinalproduct": "ADVIL", "seriousnessdeath": "Yes"}},
    # # ====== Tests for FAERS_count_drugs_by_drug_event ======
    # {"name": "FAERS_count_drugs_by_drug_event", "arguments": {"patient.patientsex": "Female"}},
    # {"name": "FAERS_count_drugs_by_drug_event", "arguments": {"patient.patientagegroup": "Child"}},
    # {"name": "FAERS_count_drugs_by_drug_event", "arguments": {"serious": "Serious"}},
    # {"name": "FAERS_count_drugs_by_drug_event", "arguments": {"occurcountry": "CA", "serious": "Non-serious"}},
    # # ====== Tests for FAERS_count_country_by_drug_event ======
    # {"name": "FAERS_count_country_by_drug_event", "arguments": {"medicinalproduct": "METFORMIN"}},
    # {"name": "FAERS_count_country_by_drug_event", "arguments": {"medicinalproduct": "INSULIN", "patient.patientsex": "Male"}},
    # {"name": "FAERS_count_country_by_drug_event", "arguments": {"medicinalproduct": "ASPIRIN", "serious": "Serious"}},
    # {"name": "FAERS_count_country_by_drug_event", "arguments": {"medicinalproduct": "STATIN", "patient.patientsex": "Female", "patient.patientagegroup": "Adult", "serious": "Non-serious"}},
    # # ====== Tests for FAERS_count_reportercountry_by_drug_event ======
    # {"name": "FAERS_count_reportercountry_by_drug_event", "arguments": {"medicinalproduct": "LANTUS"}},
    # {"name": "FAERS_count_reportercountry_by_drug_event", "arguments": {"medicinalproduct": "AMLODIPINE", "patient.patientsex": "Unknown"}},
    # {"name": "FAERS_count_reportercountry_by_drug_event", "arguments": {"medicinalproduct": "ATORVASTATIN", "patient.patientagegroup": "Elderly"}},
    # {"name": "FAERS_count_reportercountry_by_drug_event", "arguments": {"medicinalproduct": "GABAPENTIN", "patient.patientsex": "Male", "patient.patientagegroup": "Adult", "serious": "Serious"}},
    # # ====== Tests for FAERS_count_seriousness_by_drug_event ======
    # {"name": "FAERS_count_seriousness_by_drug_event", "arguments": {"medicinalproduct": "NAPROXEN"}},
    # {"name": "FAERS_count_seriousness_by_drug_event", "arguments": {"medicinalproduct": "ALBUTEROL", "patient.patientsex": "Female"}},
    # {"name": "FAERS_count_seriousness_by_drug_event", "arguments": {"medicinalproduct": "PREDNISONE", "patient.patientagegroup": "Child"}},
    # {"name": "FAERS_count_seriousness_by_drug_event", "arguments": {"medicinalproduct": "METHOTREXATE", "patient.patientsex": "Male", "patient.patientagegroup": "Adult", "occurcountry": "US"}},
    # # ====== Tests for FAERS_count_outcomes_by_drug_event ======
    # {"name": "FAERS_count_outcomes_by_drug_event", "arguments": {"medicinalproduct": "IBUPROFEN"}},
    # {"name": "FAERS_count_outcomes_by_drug_event", "arguments": {"medicinalproduct": "IBUPROFEN", "patient.patientsex": "Female", "occurcountry": "GB"}},
    # {"name": "FAERS_count_outcomes_by_drug_event", "arguments": {"medicinalproduct": "IBUPROFEN", "patient.patientsex": "Male", "patient.patientagegroup": "Adolescent"}},
    # # ====== Tests for FAERS_count_drug_routes_by_event ======
    # {"name": "FAERS_count_drug_routes_by_event", "arguments": {"medicinalproduct": "INSULIN", "serious": "Serious"}},
    # {"name": "FAERS_count_drug_routes_by_event", "arguments": {"medicinalproduct": "MORPHINE", "serious": "Non-serious"}},
    # # ====== Tests for FAERS_count_patient_age_distribution ======
    # {"name": "FAERS_count_patient_age_distribution", "arguments": {"medicinalproduct": "PENICILLIN"}},
    # {"name": "FAERS_count_patient_age_distribution", "arguments": {"medicinalproduct": "ACETAMINOPHEN"}},
    # ====== Tests for FAERS_count_death_related_by_drug ======
    # {"name": "FAERS_count_death_related_by_drug", "arguments": {"medicinalproduct": "FENTANYL"}},
    # {"name": "FAERS_count_death_related_by_drug", "arguments": {"medicinalproduct": "WARFARIN"}},
    # # ====== Tests for FAERS_count_additive_adverse_reactions ======
    # {"name": "FAERS_count_additive_adverse_reactions", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"]}},
    # {"name": "FAERS_count_additive_adverse_reactions", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"], "patient.patientsex": "Male"}},
    # {"name": "FAERS_count_additive_adverse_reactions", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"], "serious": "Serious"}},
    # # ====== Tests for FAERS_count_additive_event_reports_by_country ======
    # {"name": "FAERS_count_additive_event_reports_by_country", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"]}},
    # {"name": "FAERS_count_additive_event_reports_by_country", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"], "serious": "Non-serious"}},
    # # ====== Tests for FAERS_count_additive_reports_by_reporter_country ======
    # {"name": "FAERS_count_additive_reports_by_reporter_country", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"]}},
    # {"name": "FAERS_count_additive_reports_by_reporter_country", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"], "patient.patientagegroup": "Elderly"}},
    # # ====== Tests for FAERS_count_additive_seriousness_classification ======
    # {"name": "FAERS_count_additive_seriousness_classification", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"]}},
    # {"name": "FAERS_count_additive_seriousness_classification", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"], "occurcountry": "CA"}},
    # ====== Tests for FAERS_count_additive_reaction_outcomes ======
    # {"name": "FAERS_count_additive_reaction_outcomes", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"]}},
    # {"name": "FAERS_count_additive_reaction_outcomes", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"]}},
    # ====== Tests for FAERS_count_additive_administration_routes ======
    # {"name": "FAERS_count_additive_administration_routes", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"]}},
    # {"name": "FAERS_count_additive_administration_routes", "arguments": {"medicinalproducts": ["LIPITOR", "ASPIRIN"], "serious": "Non-serious"}},
    #            {'name': 'FAERS_count_additive_seriousness_classification', 'arguments': {'medicinalproducts': ['Dysport'], 'occurcountry': 'US', 'patient.patientagegroup': 'Adult'}},
    {
        "name": "FDA_get_drug_names_by_clinical_studies",
        "arguments": {
            "clinical_studies": "NSCLC hepatic impairment",
            "indication": "cardiovascular",
        },
    },
]

# Step 3: Run all test queries
for idx, query in enumerate(test_queries):
    try:
        print(
            f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
        )
        result = tooluni.run(query)
        print("✅ Success. Example output snippet:")
        print(
            result if isinstance(result, dict) else str(result)[:500]
        )  # Print snippet if result is big
    except Exception as e:
        print(f"❌ Failed. Error: {str(e)}")
