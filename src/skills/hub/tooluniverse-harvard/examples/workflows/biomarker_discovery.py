#!/usr/bin/env python3
"""
Enhanced Biomarker Discovery Workflow

Professional biomarker discovery pipeline with protein interactions,
pathway enrichment analysis, and literature validation.
"""

from tooluniverse.tools import (
    HPA_search_genes_by_query,
    GO_get_annotations_for_gene,
    humanbase_ppi_analysis,
    enrichr_gene_enrichment_analysis,
    EuropePMC_search_articles,
    search_clinical_trials,
)


def biomarker_discovery_workflow(candidate_genes: list, cancer_type: str):
    """
    Enhanced biomarker discovery workflow with protein interactions and pathway analysis.

    Args:
        candidate_genes: List of candidate biomarker genes
        cancer_type: Type of cancer to analyze

    Returns:
        dict: Structured results with gene analysis, PPI network, enrichment, and ranking
    """
    print(f"=== Biomarker Discovery Workflow for {cancer_type} ===")

    results = {
        "cancer_type": cancer_type,
        "genes": [],
        "ppi": None,
        "enrichment": {},
        "literature_hits": 0,
        "ranked_biomarkers": [],
    }

    # Step 1: Gene expression analysis
    print(f"\n1. Analyzing {len(candidate_genes)} candidate genes...")
    gene_data = {}
    for gene in candidate_genes[:3]:  # Analyze top 3 genes
        print(f"   Analyzing {gene}...")

        # Search for gene information
        gene_search = HPA_search_genes_by_query(search_query=gene)

        if gene_search and 'genes' in gene_search:
            gene_info = gene_search['genes'][0]
            ensembl_id = gene_info['ensembl_id']
            gene_data[gene] = ensembl_id
            results["genes"].append({"symbol": gene, "ensembl_id": ensembl_id})
            print(f"     Ensembl ID: {ensembl_id}")

            # Get GO annotations
            go_annotations = GO_get_annotations_for_gene(gene_id=ensembl_id)
            if go_annotations:
                print(f"     GO annotations: {len(go_annotations)}")

    # Step 2: Protein-protein interaction analysis
    print("\n2. Analyzing protein-protein interactions...")
    if gene_data:
        gene_list = list(gene_data.values())[:5]  # Use first 5 genes
        ppi_analysis = humanbase_ppi_analysis(
            gene_list=gene_list,
            tissue=cancer_type.lower().replace(' ', '_'),
            max_node=10,
            interaction="co-expression",
            string_mode=True
        )

        if ppi_analysis:
            print("   PPI network analysis completed")
            if isinstance(ppi_analysis, dict):
                print(f"   Network nodes: {len(ppi_analysis.get('nodes', []))}")
                print(f"   Network edges: {len(ppi_analysis.get('edges', []))}")
            else:
                print("   PPI analysis result available")
            results["ppi"] = ppi_analysis

    # Step 3: Pathway enrichment analysis
    print("\n3. Performing pathway enrichment analysis...")
    if gene_data:
        gene_symbols = list(gene_data.keys())
        enrichment_libs = [
            "WikiPathways_2024_Human",
            "Reactome_Pathways_2024",
            "MSigDB_Hallmark_2020",
            "GO_Molecular_Function_2023",
            "GO_Biological_Process_2023"
        ]

        pathway_analysis = enrichr_gene_enrichment_analysis(
            gene_list=gene_symbols,
            libs=enrichment_libs
        )

        if pathway_analysis:
            print("   Pathway enrichment completed")
            for lib in enrichment_libs:
                if lib in pathway_analysis:
                    # Keep only significant terms (q<0.05)
                    terms = pathway_analysis[lib]
                    filtered = []
                    for t in terms:
                        adj = t.get("adjusted_p_value") or t.get("Adjusted P-value")
                        if adj is None or adj < 0.05:
                            filtered.append(t)
                    results["enrichment"][lib] = filtered
                    print(f"     {lib}: {len(filtered)} enriched pathways (q<0.05)")

    # Step 4: Literature search
    print("\n4. Searching biomarker literature...")
    biomarker_papers = EuropePMC_search_articles(
        query=f"{cancer_type} biomarker gene expression",
        limit=10
    )

    if biomarker_papers:
        results["literature_hits"] = len(biomarker_papers)
        print(f"   Found {results['literature_hits']} biomarker papers")

    # Step 5: Clinical trial search
    print("\n5. Searching clinical trials...")
    trials = search_clinical_trials(
        query_term=f"{cancer_type} biomarker",
        condition=cancer_type,
        pageSize=5
    )

    if trials and 'results' in trials:
        print(f"   Found {len(trials['results'])} clinical trials")

    # Step 6: Biomarker ranking
    print("\n6. Ranking biomarkers by evidence...")
    gene_scores = []
    for g in results["genes"]:
        symbol = g["symbol"]
        enrich_count = 0
        for lib, terms in results["enrichment"].items():
            for t in terms:
                genes_field = t.get("genes") or t.get("overlap_genes") or []
                if isinstance(genes_field, str):
                    genes_list = [x.strip() for x in genes_field.split(',')]
                else:
                    genes_list = genes_field
                if symbol in genes_list:
                    enrich_count += 1
        score = enrich_count + (results["literature_hits"] > 0) * 0.5
        gene_scores.append({"symbol": symbol, "score": score})
    gene_scores.sort(key=lambda x: -x["score"])
    results["ranked_biomarkers"] = gene_scores

    print("\n=== Biomarker Discovery Workflow Complete ===")
    return results


if __name__ == "__main__":
    # Example usage
    results = biomarker_discovery_workflow(
        candidate_genes=["BRCA1", "BRCA2", "TP53", "PTEN", "PIK3CA"],
        cancer_type="Breast cancer"
    )
    
    print(f"\nResults summary:")
    print(f"- Cancer type: {results['cancer_type']}")
    print(f"- Genes analyzed: {len(results['genes'])}")
    print(f"- Literature hits: {results['literature_hits']}")
    print(f"- Top biomarkers: {[b['symbol'] for b in results['ranked_biomarkers'][:3]]}")

