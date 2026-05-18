#!/usr/bin/env python3
"""
ADMETAI Tool Usage Example

This example demonstrates how to use the ADMETAI tools in ToolUniverse
to predict various ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity)
properties of chemical compounds.

The example shows:
1. How to initialize ToolUniverse
2. How to use ADMETAI_predict_physicochemical_properties
3. How to use ADMETAI_predict_CYP_interactions
4. How to use other ADMETAI prediction tools

Requirements:
- ToolUniverse installed
- Valid API keys for ADMETAI services (if required)
"""

from tooluniverse import ToolUniverse
import json


def main():
    """Main function demonstrating ADMETAI tool usage."""
    print("🧪 ADMETAI Tool Usage Example")
    print("=" * 50)
    
    # Initialize ToolUniverse
    print("Initializing ToolUniverse...")
    tooluni = ToolUniverse()
    tooluni.load_tools()
    print("✅ ToolUniverse initialized successfully")
    
    # Example queries demonstrating different ADMETAI tools
    example_queries = [
    {
        "name": "ADMETAI_predict_physicochemical_properties",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_CYP_interactions",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_BBB_penetrance",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_toxicity",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_bioavailability",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_clearance_distribution",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_nuclear_receptor_activity",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_stress_response",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    {
        "name": "ADMETAI_predict_solubility_lipophilicity_hydration",
        "arguments": {
            "smiles": [
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)[O-])C21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[K+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@H](O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCC(O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)O)C21",
                "CCC(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC(O)CC(O)CC(=O)[O-])C21.[Na+]",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CCC(C)C(=O)OC1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)NO)[C@H]21",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H](O)C[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)O)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CCCC[C@@H](O)CC(=O)[O-])[C@H]21.[Na+]",
                "CC[C@@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21.[NaH]",
                "CCC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@@H]1C[C@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@@H](C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](O)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
                "CC(C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)C21",
                "C[C@H]1C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]2[C@@H](OC(=O)[C@@H](C)CCO)C1",
                "CC(O)[C@H](C)C(=O)O[C@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@H]21",
            ]
        },
    },
    ]
    
    # Run example queries
    print(f"\nRunning {len(example_queries)} example queries...")
    
    for idx, query in enumerate(example_queries, 1):
        print(f"\n[{idx}] Running tool: {query['name']}")
        print(f"Arguments: {json.dumps(query['arguments'], indent=2)}")
        
        try:
            result = tooluni.run(query)
            print("✅ Success! Result:")
            if isinstance(result, dict):
                print(json.dumps(result, indent=2))
            else:
                print(str(result))
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n🎉 ADMETAI Tool Example completed!")


if __name__ == "__main__":
    main()
