#!/usr/bin/env python3
"""
Quick Start Guide for Visualization Tools
==========================================

A simple, beginner-friendly guide to using ToolUniverse visualization tools.
Perfect for getting started quickly!

Prerequisites:
- pip install tooluniverse[visualization]
"""

from tooluniverse import ToolUniverse

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

print("🎨 ToolUniverse Visualization Tools - Quick Start")
print("=" * 50)

# 1. Protein 3D Structure Visualization
print("\n1. 🧬 Protein 3D Structure")
result = tu.run({
    "name": "visualize_protein_structure_3d",
    "arguments": {
        "pdb_id": "1CRN",  # Crambin protein
        "style": "cartoon",
        "color_scheme": "spectrum"
    }
})

if result["success"]:
    print("✅ Protein structure visualized!")
    # Save HTML to file
    with open("protein_example.html", "w") as f:
        f.write(result["visualization"]["html"])
    print("💾 Saved to: protein_example.html")
else:
    print(f"❌ Error: {result['error']}")

# 2. Molecule 2D Structure Visualization
print("\n2. 🧪 Molecule 2D Structure")
result = tu.run({
    "name": "visualize_molecule_2d",
    "arguments": {
        "smiles": "CCO",  # Ethanol
        "width": 400,
        "height": 400
    }
})

if result["success"]:
    print("✅ Molecule 2D structure visualized!")
    with open("molecule_2d_example.html", "w") as f:
        f.write(result["visualization"]["html"])
    print("💾 Saved to: molecule_2d_example.html")
else:
    print(f"❌ Error: {result['error']}")

# 3. Molecule 3D Structure Visualization
print("\n3. 🔬 Molecule 3D Structure")
result = tu.run({
    "name": "visualize_molecule_3d",
    "arguments": {
        "smiles": "CCO",  # Ethanol
        "style": "stick",
        "color_scheme": "default"
    }
})

if result["success"]:
    print("✅ Molecule 3D structure visualized!")
    with open("molecule_3d_example.html", "w") as f:
        f.write(result["visualization"]["html"])
    print("💾 Saved to: molecule_3d_example.html")
else:
    print(f"❌ Error: {result['error']}")

print("\n🎉 Quick start completed!")
print("📁 Open the generated HTML files in your browser to view the visualizations.")
print("📚 For more examples, see: examples/visualization_examples.py")
