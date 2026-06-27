#!/usr/bin/env python3
"""
Gene Expression Analysis Workflow

Professional gene expression analysis pipeline using HPA (Human Protein Atlas)
for comprehensive gene expression profiling and analysis.
"""

from tooluniverse.tools import (
    HPA_search_genes_by_query,
    HPA_get_comprehensive_gene_details_by_ensembl_id,
    HPA_get_comparative_expression_by_gene_and_cellline,
    HPA_get_cancer_prognostics_by_gene,
    HPA_get_biological_processes_by_gene,
    HPA_get_disease_expression_by_gene_tissue_disease,
    GO_get_annotations_for_gene,
    enrichr_gene_enrichment_analysis,
)


def gene_expression_analysis_workflow(gene_list: list, cancer_type: str = "breast cancer"):
    """
    Comprehensive gene expression analysis workflow.

    Args:
        gene_list: List of genes to analyze
        cancer_type: Type of cancer for disease-specific analysis

    Returns:
        dict: Structured results with expression data, annotations, and pathways
    """
    print(f"=== Gene Expression Analysis Workflow ===")
    print(f"Analyzing {len(gene_list)} genes for {cancer_type}")

    results = {
        "genes": [],
        "expression_data": {},
        "cancer_prognostics": {},
        "biological_processes": {},
        "pathway_enrichment": {},
        "disease_expression": {},
    }

    # Step 1: Gene information retrieval
    print("\n1. Retrieving gene information...")
    for gene in gene_list:
        print(f"   Analyzing {gene}...")
        
        # Search for gene
        gene_search = HPA_search_genes_by_query(search_query=gene)
        
        if gene_search and 'genes' in gene_search and gene_search['genes']:
            gene_info = gene_search['genes'][0]
            ensembl_id = gene_info['ensembl_id']
            gene_symbol = gene_info['gene_name']
            
            print(f"     Ensembl ID: {ensembl_id}")
            print(f"     Gene symbol: {gene_symbol}")
            
            # Store basic gene info
            results["genes"].append({
                "symbol": gene_symbol,
                "ensembl_id": ensembl_id,
                "query": gene
            })

    # Step 2: Comprehensive gene details
    print("\n2. Retrieving comprehensive gene details...")
    for gene_data in results["genes"]:
        ensembl_id = gene_data["ensembl_id"]
        symbol = gene_data["symbol"]
        
        print(f"   Getting details for {symbol}...")
        
        try:
            details = HPA_get_comprehensive_gene_details_by_ensembl_id(
                ensembl_id=ensembl_id
            )
            if details:
                print(f"     Retrieved comprehensive details")
                results["expression_data"][symbol] = details
        except Exception as e:
            print(f"     Error getting details: {str(e)}")

    # Step 3: Comparative expression analysis
    print("\n3. Analyzing comparative expression...")
    for gene_data in results["genes"]:
        ensembl_id = gene_data["ensembl_id"]
        symbol = gene_data["symbol"]
        
        print(f"   Analyzing expression for {symbol}...")
        
        try:
            # Get expression in different cell lines
            expression = HPA_get_comparative_expression_by_gene_and_cellline(
                ensembl_id=ensembl_id
            )
            if expression:
                print(f"     Found expression data")
                results["expression_data"][symbol]["comparative"] = expression
        except Exception as e:
            print(f"     Error getting expression: {str(e)}")

    # Step 4: Cancer prognostic analysis
    print("\n4. Analyzing cancer prognostic significance...")
    for gene_data in results["genes"]:
        ensembl_id = gene_data["ensembl_id"]
        symbol = gene_data["symbol"]
        
        print(f"   Analyzing cancer prognosis for {symbol}...")
        
        try:
            prognostics = HPA_get_cancer_prognostics_by_gene(ensembl_id=ensembl_id)
            if prognostics:
                print(f"     Found prognostic data")
                results["cancer_prognostics"][symbol] = prognostics
        except Exception as e:
            print(f"     Error getting prognostics: {str(e)}")

    # Step 5: Biological process analysis
    print("\n5. Analyzing biological processes...")
    for gene_data in results["genes"]:
        ensembl_id = gene_data["ensembl_id"]
        symbol = gene_data["symbol"]
        
        print(f"   Analyzing biological processes for {symbol}...")
        
        try:
            processes = HPA_get_biological_processes_by_gene(ensembl_id=ensembl_id)
            if processes:
                print(f"     Found {len(processes)} biological processes")
                results["biological_processes"][symbol] = processes
        except Exception as e:
            print(f"     Error getting processes: {str(e)}")

    # Step 6: Disease-specific expression
    print(f"\n6. Analyzing disease-specific expression for {cancer_type}...")
    for gene_data in results["genes"]:
        ensembl_id = gene_data["ensembl_id"]
        symbol = gene_data["symbol"]
        
        print(f"   Analyzing disease expression for {symbol}...")
        
        try:
            disease_expr = HPA_get_disease_expression_by_gene_tissue_disease(
                ensembl_id=ensembl_id,
                tissue=cancer_type.lower().replace(' ', '_'),
                disease=cancer_type.lower().replace(' ', '_')
            )
            if disease_expr:
                print(f"     Found disease expression data")
                results["disease_expression"][symbol] = disease_expr
        except Exception as e:
            print(f"     Error getting disease expression: {str(e)}")

    # Step 7: Pathway enrichment analysis
    print("\n7. Performing pathway enrichment analysis...")
    gene_symbols = [g["symbol"] for g in results["genes"]]
    
    if gene_symbols:
        enrichment_libs = [
            "GO_Biological_Process_2023",
            "GO_Molecular_Function_2023",
            "MSigDB_Hallmark_2020",
            "Reactome_Pathways_2024"
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

    print("\n=== Gene Expression Analysis Workflow Complete ===")
    return results


if __name__ == "__main__":
    # Example usage
    results = gene_expression_analysis_workflow(
        gene_list=["BRCA1", "BRCA2", "TP53", "PTEN", "PIK3CA"],
        cancer_type="breast cancer"
    )
    
    print(f"\nResults summary:")
    print(f"- Genes analyzed: {len(results['genes'])}")
    print(f"- Expression data: {len(results['expression_data'])} genes")
    print(f"- Cancer prognostics: {len(results['cancer_prognostics'])} genes")
    print(f"- Biological processes: {len(results['biological_processes'])} genes")
    print(f"- Pathway enrichment: {len(results['pathway_enrichment'])} libraries")

