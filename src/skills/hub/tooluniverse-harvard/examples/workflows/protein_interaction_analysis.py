#!/usr/bin/env python3
"""
Protein Interaction Analysis Workflow

Professional protein-protein interaction analysis pipeline using HumanBase
for comprehensive network analysis and functional annotation.
"""

from tooluniverse.tools import (
    humanbase_ppi_analysis,
    HPA_search_genes_by_query,
    GO_get_annotations_for_gene,
    enrichr_gene_enrichment_analysis,
)


def protein_interaction_analysis_workflow(gene_list: list, tissue: str = "breast", interaction_type: str = "co-expression"):
    """
    Comprehensive protein-protein interaction analysis workflow.

    Args:
        gene_list: List of genes to analyze
        tissue: Tissue type for analysis
        interaction_type: Type of interaction to analyze

    Returns:
        dict: Structured results with PPI network, annotations, and pathway analysis
    """
    print(f"=== Protein Interaction Analysis Workflow ===")
    print(f"Analyzing {len(gene_list)} genes in {tissue} tissue")

    results = {
        "input_genes": gene_list,
        "tissue": tissue,
        "interaction_type": interaction_type,
        "ppi_network": None,
        "gene_annotations": {},
        "pathway_enrichment": {},
        "network_stats": {},
    }

    # Step 1: Gene validation and Ensembl ID mapping
    print("\n1. Validating genes and mapping to Ensembl IDs...")
    ensembl_ids = []
    for gene in gene_list:
        print(f"   Validating {gene}...")
        
        try:
            gene_search = HPA_search_genes_by_query(search_query=gene)
            if gene_search and 'genes' in gene_search and gene_search['genes']:
                gene_info = gene_search['genes'][0]
                ensembl_id = gene_info['ensembl_id']
                ensembl_ids.append(ensembl_id)
                print(f"     Mapped to Ensembl ID: {ensembl_id}")
                
                # Store gene annotation
                results["gene_annotations"][gene] = {
                    "ensembl_id": ensembl_id,
                    "gene_name": gene_info['gene_name']
                }
            else:
                print(f"     Warning: Could not find Ensembl ID for {gene}")
        except Exception as e:
            print(f"     Error validating {gene}: {str(e)}")

    if not ensembl_ids:
        print("   Error: No valid Ensembl IDs found")
        return results

    # Step 2: Protein-protein interaction analysis
    print(f"\n2. Analyzing protein-protein interactions...")
    print(f"   Using {len(ensembl_ids)} genes for PPI analysis")
    
    try:
        ppi_analysis = humanbase_ppi_analysis(
            gene_list=ensembl_ids,
            tissue=tissue,
            max_node=20,
            interaction=interaction_type,
            string_mode=True
        )
        
        if ppi_analysis:
            print("   PPI network analysis completed")
            results["ppi_network"] = ppi_analysis
            
            # Extract network statistics
            if isinstance(ppi_analysis, dict):
                nodes = ppi_analysis.get('nodes', [])
                edges = ppi_analysis.get('edges', [])
                results["network_stats"] = {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "input_genes_in_network": len([n for n in nodes if n in ensembl_ids])
                }
                print(f"     Network nodes: {len(nodes)}")
                print(f"     Network edges: {len(edges)}")
                print(f"     Input genes in network: {results['network_stats']['input_genes_in_network']}")
            else:
                print("     PPI analysis completed (string mode)")
                results["network_stats"] = {"status": "completed_string_mode"}
        else:
            print("   No PPI network found")
    except Exception as e:
        print(f"   Error in PPI analysis: {str(e)}")

    # Step 3: Gene annotation analysis
    print("\n3. Analyzing gene annotations...")
    for gene, annotation in results["gene_annotations"].items():
        ensembl_id = annotation["ensembl_id"]
        print(f"   Getting GO annotations for {gene}...")
        
        try:
            go_annotations = GO_get_annotations_for_gene(gene_id=ensembl_id)
            if go_annotations:
                print(f"     Found {len(go_annotations)} GO annotations")
                annotation["go_annotations"] = go_annotations
            else:
                annotation["go_annotations"] = []
        except Exception as e:
            print(f"     Error getting GO annotations: {str(e)}")
            annotation["go_annotations"] = []

    # Step 4: Pathway enrichment analysis
    print("\n4. Performing pathway enrichment analysis...")
    gene_symbols = [annotation["gene_name"] for annotation in results["gene_annotations"].values()]
    
    if gene_symbols:
        enrichment_libs = [
            "GO_Biological_Process_2023",
            "GO_Molecular_Function_2023",
            "MSigDB_Hallmark_2020",
            "Reactome_Pathways_2024",
            "KEGG_2021_Human"
        ]
        
        try:
            pathway_analysis = enrichr_gene_enrichment_analysis(
                gene_list=gene_symbols,
                libs=enrichment_libs
            )
            
            if pathway_analysis:
                print("   Pathway enrichment completed")
                for lib in enrichment_libs:
                    if lib in pathway_analysis:
                        # Filter significant terms (q<0.05)
                        terms = pathway_analysis[lib]
                        filtered = []
                        for t in terms:
                            adj = t.get("adjusted_p_value") or t.get("Adjusted P-value")
                            if adj is None or adj < 0.05:
                                filtered.append(t)
                        results["pathway_enrichment"][lib] = filtered
                        print(f"     {lib}: {len(filtered)} enriched pathways (q<0.05)")
        except Exception as e:
            print(f"   Error in pathway enrichment: {str(e)}")

    # Step 5: Network analysis summary
    print("\n5. Generating network analysis summary...")
    if results["ppi_network"] and isinstance(results["ppi_network"], dict):
        nodes = results["ppi_network"].get('nodes', [])
        edges = results["ppi_network"].get('edges', [])
        
        # Calculate basic network metrics
        if edges:
            # Count interactions per gene
            interaction_counts = {}
            for edge in edges:
                source = edge.get('source', '')
                target = edge.get('target', '')
                if source in interaction_counts:
                    interaction_counts[source] += 1
                else:
                    interaction_counts[source] = 1
                if target in interaction_counts:
                    interaction_counts[target] += 1
                else:
                    interaction_counts[target] = 1
            
            # Find highly connected genes
            sorted_genes = sorted(interaction_counts.items(), key=lambda x: x[1], reverse=True)
            results["network_stats"]["highly_connected_genes"] = sorted_genes[:5]
            print(f"     Top connected genes: {[g[0] for g in sorted_genes[:3]]}")

    print("\n=== Protein Interaction Analysis Workflow Complete ===")
    return results


if __name__ == "__main__":
    # Example usage
    results = protein_interaction_analysis_workflow(
        gene_list=["BRCA1", "BRCA2", "TP53", "PTEN", "PIK3CA"],
        tissue="breast",
        interaction_type="co-expression"
    )
    
    print(f"\nResults summary:")
    print(f"- Input genes: {len(results['input_genes'])}")
    print(f"- Tissue: {results['tissue']}")
    print(f"- Network nodes: {results['network_stats'].get('total_nodes', 'N/A')}")
    print(f"- Network edges: {results['network_stats'].get('total_edges', 'N/A')}")
    print(f"- Pathway enrichment: {len(results['pathway_enrichment'])} libraries")

