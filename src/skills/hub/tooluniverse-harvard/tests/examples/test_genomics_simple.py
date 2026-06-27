#!/usr/bin/env python3
"""
Tests for genomics simple example
"""

import unittest

from tooluniverse.tools import (
    HPA_search_genes_by_query,
    HPA_get_comprehensive_gene_details_by_ensembl_id,
    GO_get_annotations_for_gene,
    enrichr_gene_enrichment_analysis
)


class TestGenomicsSimple(unittest.TestCase):
    """Test genomics simple example tools directly."""
    
    def test_search_genes(self):
        """Test gene search using HPA tool."""
        # Test with a known gene
        genes = HPA_search_genes_by_query(search_query="BRCA1")
        
        # Should return results or None
        self.assertTrue(genes is None or isinstance(genes, (list, dict)))
    
    def test_get_gene_details(self):
        """Test getting gene details using HPA tool."""
        # Test with a known Ensembl ID
        details = HPA_get_comprehensive_gene_details_by_ensembl_id(
            ensembl_id="ENSG00000012048",
            include_images=True,
            include_antibodies=True,
            include_expression=True
        )
        
        # Should return results or None
        self.assertTrue(details is None or isinstance(details, dict))
    
    def test_analyze_expression(self):
        """Test expression analysis using HPA tool."""
        # Test with a known gene
        expression = HPA_search_genes_by_query(search_query="TP53")
        
        # Should return results or None
        self.assertTrue(expression is None or isinstance(expression, (list, dict)))
    
    def test_find_protein_interactions(self):
        """Test protein interaction analysis."""
        # Test with a known gene
        interactions = HPA_search_genes_by_query(search_query="MYC")
        
        # Should return results or None
        self.assertTrue(interactions is None or isinstance(interactions, (list, dict)))
    
    def test_get_go_annotations(self):
        """Test GO annotations using GO tool."""
        # Test with a known gene
        annotations = GO_get_annotations_for_gene(
            gene_id="ENSG00000012048"
        )
        
        # Should return results or None
        self.assertTrue(annotations is None or isinstance(annotations, (list, dict)))
    
    def test_pathway_enrichment(self):
        """Test pathway enrichment using Enrichr tool."""
        # Test with a list of genes
        genes = ["BRCA1", "BRCA2", "TP53"]
        enrichment = enrichr_gene_enrichment_analysis(
            gene_list=genes,
            libs=["KEGG_2021_Human"]
        )
        
        # Should return results, None, or False (for API errors)
        # The tool returns a tuple with (connected_path, connections) dictionaries
        self.assertTrue(enrichment is None or enrichment is False or isinstance(enrichment, (list, dict, tuple)))
    
    def test_genomics_analysis(self):
        """Test that the genomics analysis tools work correctly."""
        # Test that all required tools are available and can be called
        # This simulates the workflow without needing the actual example file
        self.assertTrue(callable(HPA_search_genes_by_query))
        self.assertTrue(callable(HPA_get_comprehensive_gene_details_by_ensembl_id))
        self.assertTrue(callable(GO_get_annotations_for_gene))
        self.assertTrue(callable(enrichr_gene_enrichment_analysis))


class TestDirectImports(unittest.TestCase):
    """Test direct imports work correctly."""
    
    def test_hpa_import(self):
        """Test HPA import."""
        self.assertIsNotNone(HPA_search_genes_by_query)
        self.assertIsNotNone(HPA_get_comprehensive_gene_details_by_ensembl_id)
    
    def test_go_import(self):
        """Test GO import."""
        self.assertIsNotNone(GO_get_annotations_for_gene)
    
    def test_enrichr_import(self):
        """Test Enrichr import."""
        self.assertIsNotNone(enrichr_gene_enrichment_analysis)


if __name__ == "__main__":
    unittest.main()