from tooluniverse import ToolUniverse

# Step 1: Initialize tool universe
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define test queries
# commented out = already tested but didn't add return_Schema. uncommented = not tested.
test_queries = [
    {"name": "get_sequence_by_pdb_id", "arguments": {"pdb_id": "1XYZ"}},
    {"name": "get_protein_metadata_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_polymer_entity_ids_by_pdb_id", "arguments": {"pdb_id": "1A3N"}},
    {
        "name": "get_polymer_entity_type_by_entity_id",
        "arguments": {"entity_id": "1A8M_1"},
    },
    {"name": "get_source_organism_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_citation_info_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_sequence_lengths_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_mutation_annotations_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {
        "name": "get_em_3d_fitting_and_reconstruction_details",
        "arguments": {"pdb_id": "6VXX"},
    },
    {"name": "get_assembly_summary", "arguments": {"assembly_id": "1A8M-1"}},
    {"name": "get_assembly_info_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_taxonomy_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_release_deposit_dates_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_host_organism_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_ec_number_by_entity_id", "arguments": {"entity_id": "1T5D_1"}},
    {"name": "get_gene_name_by_entity_id", "arguments": {"entity_id": "3W2S_1"}},
    {
        "name": "get_polymer_molecular_weight_by_entity_id",
        "arguments": {"entity_id": "1A8M_1"},
    },
    {"name": "get_ligand_bond_count_by_pdb_id", "arguments": {"pdb_id": "1T5D"}},
    {
        "name": "get_crystal_growth_conditions_by_pdb_id",
        "arguments": {"pdb_id": "1A8M"},
    },
    {"name": "get_polymer_entity_annotations", "arguments": {"entity_id": "1T5D_1"}},
    {
        "name": "get_oligosaccharide_descriptors_by_entity_id",
        "arguments": {"entity_id": "5FMB_2"},
    },
    {
        "name": "get_sequence_positional_features_by_instance_id",
        "arguments": {"instance_id": "1NDO.A"},
    },
    {
        "name": "get_crystallographic_properties_by_pdb_id",
        "arguments": {"pdb_id": "1A8M"},
    },
    {
        "name": "get_structure_validation_metrics_by_pdb_id",
        "arguments": {"pdb_id": "1A8M"},
    },
    {"name": "get_structure_title_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_polymer_entity_count_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_emdb_ids_by_pdb_id", "arguments": {"pdb_id": "6VXX"}},
    {
        "name": "get_uniprot_accession_by_entity_id",
        "arguments": {"entity_id": "1A8M_1"},
    },
    {"name": "get_crystallization_ph_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_space_group_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_protein_classification_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {
        "name": "get_structure_determination_software_by_pdb_id",
        "arguments": {"pdb_id": "1A8M"},
    },
    {"name": "get_refinement_resolution_by_pdb_id", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_binding_affinity_by_pdb_id", "arguments": {"pdb_id": "3W2S"}},
    {"name": "get_ligand_smiles_by_chem_comp_id", "arguments": {"chem_comp_id": "ATP"}},
    {"name": "get_core_refinement_statistics", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_target_cofactor_info", "arguments": {"pdb_id": "1A8M"}},
    {"name": "get_chem_comp_audit_info", "arguments": {"pdb_id": "1T5D"}},
    {"name": "get_chem_comp_charge_and_ambiguity", "arguments": {"pdb_id": "1T5D"}},
]

# Step 3: Run test queries
for query in test_queries:
    result = tooluni.run(query)
    print(f"Query: {query}")
    print("--" * 20)
    print(f"Result: {result}")
