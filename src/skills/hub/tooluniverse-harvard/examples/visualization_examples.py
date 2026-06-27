#!/usr/bin/env python3
"""
Visualization Tools Examples
============================

This file demonstrates how to use the visualization tools in ToolUniverse.
These examples show practical usage scenarios for scientific visualization.

Prerequisites:
- Install ToolUniverse with visualization dependencies: pip install tooluniverse[visualization]
- Or install manually: pip install py3Dmol rdkit plotly kaleido scipy matplotlib networkx
"""

import json
import os
import warnings
from typing import Any, Dict, List
from tooluniverse import ToolUniverse

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*RDKit.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")

# Initialize ToolUniverse
print("🔬 Initializing ToolUniverse...")
tu = ToolUniverse()
tu.load_tools()

print("✅ ToolUniverse loaded successfully!")
tool_names = [tool.get('name') for tool in tu.all_tools if isinstance(tool, dict)]
viz_tools = [tool for tool in tool_names if 'visualize' in tool]
print(f"📊 Available visualization tools: {viz_tools}")
print()


def save_visualization(result: Dict[str, Any], filename: str):
    """Save visualization HTML to file."""
    if result.get("success") and "html" in result.get("visualization", {}):
        html_content = result["visualization"]["html"]
        with open(f"visualizations/{filename}", 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"💾 Visualization saved to: visualizations/{filename}")
    else:
        print(f"❌ Failed to save visualization: {result.get('error', 'Unknown error')}")


def example_1_protein_structure_3d():
    """
    Example 1: Protein 3D Structure Visualization
    ==============================================
    
    This example shows how to visualize protein structures using PDB IDs
    and various visualization styles.
    """
    print("🧬 Example 1: Protein 3D Structure Visualization")
    print("=" * 50)
    
    # Example 1a: Basic protein visualization with PDB ID
    print("\n1a. Basic protein visualization (PDB ID: 1CRN - Crambin)")
    result = tu.run({
        "name": "visualize_protein_structure_3d",
        "arguments": {
            "pdb_id": "1CRN",
            "style": "cartoon",
            "color_scheme": "spectrum",
            "width": 800,
            "height": 600
        }
    })
    
    if result["success"]:
        print("✅ Protein structure visualization created successfully!")
        print(f"📏 Dimensions: {result['visualization']['metadata']['width']} × {result['visualization']['metadata']['height']}")
        save_visualization(result, "protein_1crn_cartoon.html")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Example 1b: Different visualization styles
    print("\n1b. Different visualization styles")
    styles = ["cartoon", "stick", "sphere", "line"]
    
    for style in styles:
        print(f"   Creating {style} style visualization...")
        result = tu.run({
            "name": "visualize_protein_structure_3d",
            "arguments": {
                "pdb_id": "1CRN",
                "style": style,
                "color_scheme": "rainbow",
                "width": 600,
                "height": 400
            }
        })
        
        if result["success"]:
            save_visualization(result, f"protein_1crn_{style}.html")
        else:
            print(f"   ❌ Failed to create {style} style: {result['error']}")
    
    # Example 1c: Advanced features
    print("\n1c. Advanced features (sidechains + surface)")
    result = tu.run({
        "name": "visualize_protein_structure_3d",
        "arguments": {
            "pdb_id": "1CRN",
            "style": "cartoon",
            "color_scheme": "ssPyMOL",
            "show_sidechains": True,
            "show_surface": True,
            "width": 1000,
            "height": 800
        }
    })
    
    if result["success"]:
        print("✅ Advanced protein visualization created!")
        save_visualization(result, "protein_1crn_advanced.html")
    else:
        print(f"❌ Error: {result['error']}")
    
    print()


def example_2_molecule_2d():
    """
    Example 2: Molecule 2D Structure Visualization
    ==============================================
    
    This example demonstrates 2D molecular structure visualization
    using SMILES, InChI, and molecule names.
    """
    print("🧪 Example 2: Molecule 2D Structure Visualization")
    print("=" * 50)
    
    # Example 2a: Basic SMILES visualization
    print("\n2a. Basic SMILES visualization")
    molecules = [
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic acid"),
        ("c1ccccc1", "Benzene"),
        ("CCN(CC)CC", "Triethylamine"),
        ("C1=CC=C(C=C1)O", "Phenol")
    ]
    
    for smiles, name in molecules:
        print(f"   Visualizing {name} ({smiles})...")
        result = tu.run({
            "name": "visualize_molecule_2d",
            "arguments": {
                "smiles": smiles,
                "width": 400,
                "height": 400,
                "output_format": "png"
            }
        })
        
        if result["success"]:
            print(f"   ✅ {name} visualization created!")
            save_visualization(result, f"molecule_2d_{name.lower().replace(' ', '_')}.html")
        else:
            print(f"   ❌ Failed to visualize {name}: {result['error']}")
    
    # Example 2b: Different output formats
    print("\n2b. Different output formats")
    formats = ["png", "svg"]
    
    for fmt in formats:
        print(f"   Creating {fmt.upper()} format...")
        result = tu.run({
            "name": "visualize_molecule_2d",
            "arguments": {
                "smiles": "CCO",
                "width": 600,
                "height": 400,
                "output_format": fmt,
                "show_atom_numbers": True,
                "show_bond_numbers": True
            }
        })
        
        if result["success"]:
            save_visualization(result, f"molecule_2d_ethanol_{fmt}.html")
        else:
            print(f"   ❌ Failed to create {fmt} format: {result['error']}")
    
    # Example 2c: Molecule name resolution
    print("\n2c. Molecule name resolution (via PubChem)")
    molecule_names = ["aspirin", "caffeine", "ibuprofen"]
    
    for name in molecule_names:
        print(f"   Resolving and visualizing {name}...")
        result = tu.run({
            "name": "visualize_molecule_2d",
            "arguments": {
                "molecule_name": name,
                "width": 500,
                "height": 500
            }
        })
        
        if result["success"]:
            print(f"   ✅ {name} resolved and visualized!")
            save_visualization(result, f"molecule_2d_{name}.html")
        else:
            print(f"   ❌ Failed to resolve {name}: {result['error']}")
    
    print()


def example_3_molecule_3d():
    """
    Example 3: Molecule 3D Structure Visualization
    ==============================================
    
    This example shows 3D molecular structure visualization
    with various styles and conformer generation.
    """
    print("🔬 Example 3: Molecule 3D Structure Visualization")
    print("=" * 50)
    
    # Example 3a: Basic 3D molecule visualization
    print("\n3a. Basic 3D molecule visualization")
    molecules_3d = [
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic acid"),
        ("c1ccccc1", "Benzene"),
        ("CCN(CC)CC", "Triethylamine")
    ]
    
    for smiles, name in molecules_3d:
        print(f"   Creating 3D visualization for {name}...")
        result = tu.run({
            "name": "visualize_molecule_3d",
            "arguments": {
                "smiles": smiles,
                "style": "stick",
                "color_scheme": "default",
                "width": 800,
                "height": 600,
                "show_hydrogens": True
            }
        })
        
        if result["success"]:
            print(f"   ✅ {name} 3D visualization created!")
            save_visualization(result, f"molecule_3d_{name.lower().replace(' ', '_')}.html")
        else:
            print(f"   ❌ Failed to visualize {name}: {result['error']}")
    
    # Example 3b: Different 3D styles
    print("\n3b. Different 3D visualization styles")
    styles_3d = ["stick", "sphere", "cartoon", "line", "spacefill"]
    
    for style in styles_3d:
        print(f"   Creating {style} style 3D visualization...")
        result = tu.run({
            "name": "visualize_molecule_3d",
            "arguments": {
                "smiles": "CCO",
                "style": style,
                "color_scheme": "spectrum",
                "width": 600,
                "height": 400,
                "show_hydrogens": False
            }
        })
        
        if result["success"]:
            save_visualization(result, f"molecule_3d_ethanol_{style}.html")
        else:
            print(f"   ❌ Failed to create {style} style: {result['error']}")
    
    # Example 3c: Advanced 3D features
    print("\n3c. Advanced 3D features (surface + conformers)")
    result = tu.run({
        "name": "visualize_molecule_3d",
        "arguments": {
            "smiles": "CCO",
            "style": "stick",
            "color_scheme": "rainbow",
            "width": 1000,
            "height": 800,
            "show_hydrogens": True,
            "show_surface": True,
            "generate_conformers": True,
            "conformer_count": 3
        }
    })
    
    if result["success"]:
        print("✅ Advanced 3D molecule visualization created!")
        print(f"📊 Generated {result['visualization']['data']['conformer_count']} conformers")
        save_visualization(result, "molecule_3d_ethanol_advanced.html")
    else:
        print(f"❌ Error: {result['error']}")
    
    print()


def example_4_integration_with_other_tools():
    """
    Example 4: Integration with Other ToolUniverse Tools
    ====================================================
    
    This example shows how visualization tools can be integrated
    with other scientific tools in ToolUniverse.
    """
    print("🔗 Example 4: Integration with Other Tools")
    print("=" * 50)
    
    # Example 4a: Protein structure from UniProt
    print("\n4a. Protein structure visualization from UniProt data")
    try:
        # First, get protein information from UniProt
        uniprot_result = tu.run({
            "name": "uniprot_search",
            "arguments": {
                "query": "hemoglobin",
                "limit": 1
            }
        })
        
        if uniprot_result.get("success") and uniprot_result.get("results"):
            protein_data = uniprot_result["results"][0]
            protein_id = protein_data.get("accession")
            
            print(f"   Found protein: {protein_data.get('protein_name')} ({protein_id})")
            
            # Now visualize the protein structure
            result = tu.run({
                "name": "visualize_protein_structure_3d",
                "arguments": {
                    "pdb_id": protein_id,
                    "style": "cartoon",
                    "color_scheme": "spectrum",
                    "width": 800,
                    "height": 600
                }
            })
            
            if result["success"]:
                print("✅ Integrated protein visualization created!")
                save_visualization(result, f"integrated_protein_{protein_id}.html")
            else:
                print(f"❌ Failed to visualize protein: {result['error']}")
        else:
            print("❌ No protein data found from UniProt")
            
    except Exception as e:
        print(f"❌ Integration example failed: {str(e)}")
    
    # Example 4b: Drug molecule visualization
    print("\n4b. Drug molecule visualization")
    try:
        # Get drug information from ChEMBL
        chembl_result = tu.run({
            "name": "chembl_search",
            "arguments": {
                "query": "aspirin",
                "limit": 1
            }
        })
        
        if chembl_result.get("success") and chembl_result.get("results"):
            drug_data = chembl_result["results"][0]
            smiles = drug_data.get("smiles")
            
            if smiles:
                print(f"   Found drug: {drug_data.get('pref_name')} ({smiles})")
                
                # Visualize the drug molecule
                result = tu.run({
                    "name": "visualize_molecule_2d",
                    "arguments": {
                        "smiles": smiles,
                        "width": 600,
                        "height": 600,
                        "show_atom_numbers": True
                    }
                })
                
                if result["success"]:
                    print("✅ Integrated drug visualization created!")
                    save_visualization(result, "integrated_drug_aspirin.html")
                else:
                    print(f"❌ Failed to visualize drug: {result['error']}")
            else:
                print("❌ No SMILES data found for drug")
        else:
            print("❌ No drug data found from ChEMBL")
            
    except Exception as e:
        print(f"❌ Drug integration example failed: {str(e)}")
    
    print()


def example_5_batch_processing():
    """
    Example 5: Batch Processing
    ============================
    
    This example demonstrates batch processing of multiple molecules
    for high-throughput visualization.
    """
    print("📊 Example 5: Batch Processing")
    print("=" * 50)
    
    # Example 5a: Batch molecule 2D visualization
    print("\n5a. Batch molecule 2D visualization")
    batch_molecules = [
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic acid"),
        ("c1ccccc1", "Benzene"),
        ("CCN(CC)CC", "Triethylamine"),
        ("C1=CC=C(C=C1)O", "Phenol"),
        ("CC(C)CO", "Isobutanol"),
        ("CC(=O)Nc1ccc(O)cc1", "Acetaminophen"),
        ("CC(C)(C)OC(=O)Nc1ccc(O)cc1", "Ibuprofen")
    ]
    
    successful_visualizations = 0
    failed_visualizations = 0
    
    for smiles, name in batch_molecules:
        print(f"   Processing {name}...")
        result = tu.run({
            "name": "visualize_molecule_2d",
            "arguments": {
                "smiles": smiles,
                "width": 300,
                "height": 300,
                "output_format": "png"
            }
        })
        
        if result["success"]:
            successful_visualizations += 1
            save_visualization(result, f"batch_{name.lower().replace(' ', '_')}.html")
        else:
            failed_visualizations += 1
            print(f"   ❌ Failed: {result['error']}")
    
    print(f"\n📈 Batch processing results:")
    print(f"   ✅ Successful: {successful_visualizations}")
    print(f"   ❌ Failed: {failed_visualizations}")
    print(f"   📊 Success rate: {successful_visualizations/(successful_visualizations+failed_visualizations)*100:.1f}%")
    
    print()


def example_6_error_handling():
    """
    Example 6: Error Handling
    ==========================
    
    This example demonstrates proper error handling
    and validation for visualization tools.
    """
    print("⚠️  Example 6: Error Handling")
    print("=" * 50)
    
    # Example 6a: Invalid parameters
    print("\n6a. Invalid parameters")
    error_cases = [
        {
            "name": "visualize_protein_structure_3d",
            "arguments": {}  # Missing required parameters
        },
        {
            "name": "visualize_molecule_2d",
            "arguments": {
                "smiles": "invalid_smiles_string"
            }
        },
        {
            "name": "visualize_molecule_3d",
            "arguments": {
                "smiles": "CCO",
                "style": "invalid_style"
            }
        }
    ]
    
    for i, case in enumerate(error_cases, 1):
        print(f"   Error case {i}: {case['name']}")
        result = tu.run(case)
        
        if result["success"]:
            print(f"   ✅ Handled gracefully: {result.get('visualization', {}).get('type', 'unknown')}")
        else:
            print(f"   ❌ Error: {result['error']}")
    
    # Example 6b: Missing dependencies
    print("\n6b. Missing dependencies handling")
    print("   (This would show dependency error messages in real scenarios)")
    
    print()


def main():
    """Run all visualization examples."""
    print("🎨 ToolUniverse Visualization Tools Examples")
    print("=" * 60)
    print()
    
    # Create visualizations directory
    os.makedirs("visualizations", exist_ok=True)
    
    try:
        # Run all examples
        example_1_protein_structure_3d()
        example_2_molecule_2d()
        example_3_molecule_3d()
        example_4_integration_with_other_tools()
        example_5_batch_processing()
        example_6_error_handling()
        
        print("🎉 All examples completed successfully!")
        print()
        print("📁 Generated files:")
        print("   All visualization HTML files are saved in the 'visualizations/' directory")
        print("   You can open them in any web browser to view the interactive visualizations")
        print()
        print("💡 Tips:")
        print("   - Use different styles and color schemes for better visualization")
        print("   - Adjust width and height parameters for different display needs")
        print("   - Enable surface and sidechain display for detailed protein analysis")
        print("   - Use batch processing for high-throughput molecular visualization")
        print("   - Always handle errors gracefully in production code")
        
    except Exception as e:
        print(f"❌ Example execution failed: {str(e)}")
        print("   Please check your ToolUniverse installation and dependencies")


if __name__ == "__main__":
    main()