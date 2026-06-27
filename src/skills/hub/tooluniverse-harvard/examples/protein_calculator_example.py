#!/usr/bin/env python3
"""
Protein Molecular Weight Calculator - Custom Tool Example

This example demonstrates how to create a custom ToolUniverse tool that
calculates the molecular weight of protein sequences. This is a complete,
working example that you can copy and modify for your own tools.

What this tool does:
- Takes a protein sequence (single-letter amino acid codes)
- Calculates the molecular weight in Daltons
- Validates the input sequence
- Returns detailed results including sequence length and cleaned sequence

How to use:
1. Save this file as protein_calculator.py
2. Import it in your code: from protein_calculator import ProteinCalculator
3. Use it with ToolUniverse as shown in the usage section below

Author: ToolUniverse Team
"""

from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool
from typing import Dict, Any


@register_tool('ProteinCalculator', config={
    "name": "protein_calculator",
    "type": "ProteinCalculator",
    "description": "Calculate molecular weight of protein sequences",
    "parameter": {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": ("Protein sequence using single-letter amino acid "
                              "codes (e.g., 'GIVEQCCTSICSLYQLENYCN')")
            }
        },
        "required": ["sequence"]
    }
})
class ProteinCalculator(BaseTool):
    """
    Calculate molecular weight of protein sequences.

    This tool takes a protein sequence and calculates its molecular weight
    by summing the molecular weights of individual amino acids and subtracting
    the weight of water molecules lost during peptide bond formation.
    """

    def __init__(self, tool_config: Dict[str, Any] = None):
        super().__init__(tool_config)

        # Amino acid molecular weights in Daltons
        # Source: https://www.thermofisher.com/us/en/home/references/
        # molecular-weights-and-conversion-tables.html
        self.aa_weights = {
            'A': 89.09,   # Alanine
            'R': 174.20,  # Arginine
            'N': 132.12,  # Asparagine
            'D': 133.10,  # Aspartic acid
            'C': 121.16,  # Cysteine
            'Q': 146.15,  # Glutamine
            'E': 147.13,  # Glutamic acid
            'G': 75.07,   # Glycine
            'H': 155.16,  # Histidine
            'I': 131.17,  # Isoleucine
            'L': 131.17,  # Leucine
            'K': 146.19,  # Lysine
            'M': 149.21,  # Methionine
            'F': 165.19,  # Phenylalanine
            'P': 115.13,  # Proline
            'S': 105.09,  # Serine
            'T': 119.12,  # Threonine
            'W': 204.23,  # Tryptophan
            'Y': 181.19,  # Tyrosine
            'V': 117.15   # Valine
        }

    def run(self, arguments=None, **kwargs) -> Dict[str, Any]:
        """
        Calculate molecular weight of a protein sequence.

        Args:
            arguments (dict, optional): Dictionary containing 'sequence' key
            **kwargs: Additional parameters (stream_callback, use_cache, validate)

        Returns:
            Dict containing molecular weight, sequence info, and success status
        """
        # Handle both direct calls and ToolUniverse calls
        if arguments is None:
            arguments = kwargs
        
        # Extract sequence from arguments
        sequence = arguments.get('sequence') if isinstance(arguments, dict) else arguments
        
        # Validate inputs
        self.validate_input(sequence=sequence)

        # Clean sequence (remove whitespace, convert to uppercase)
        clean_sequence = sequence.strip().upper()

        # Calculate molecular weight
        total_weight = sum(self.aa_weights.get(aa, 0) for aa in clean_sequence)

        # Subtract water molecules for peptide bonds
        # Each peptide bond removes one water molecule (18.015 Da)
        water_weight = (len(clean_sequence) - 1) * 18.015
        molecular_weight = total_weight - water_weight

        return {
            "molecular_weight": round(molecular_weight, 2),
            "sequence_length": len(clean_sequence),
            "sequence": clean_sequence,
            "amino_acids": list(clean_sequence),
            "success": True
        }

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If sequence is invalid
        """
        sequence = kwargs.get('sequence')

        if not sequence:
            raise ValueError("Sequence is required")

        if not isinstance(sequence, str):
            raise ValueError("Sequence must be a string")

        if len(sequence.strip()) == 0:
            raise ValueError("Sequence cannot be empty")

        # Check for valid amino acid codes
        valid_aa = set(self.aa_weights.keys())
        invalid_chars = set(sequence.upper()) - valid_aa
        if invalid_chars:
            valid_codes = ', '.join(sorted(valid_aa))
            raise ValueError(f"Invalid amino acid codes: {', '.join(invalid_chars)}. "
                           f"Valid codes are: {valid_codes}")


def demonstrate_usage():
    """
    Demonstrate how to use the ProteinCalculator tool with ToolUniverse.
    """
    print("=== Protein Molecular Weight Calculator Demo ===\n")

    # Import ToolUniverse
    from tooluniverse import ToolUniverse

    # Import our custom tool (this registers it automatically)
    # Note: The ProteinCalculator class is already defined in this file

    # Create ToolUniverse instance
    tu = ToolUniverse()
    tu.load_tools()  # Load built-in tools

    # Test sequences
    test_sequences = [
        "GIVEQCCTSICSLYQLENYCN",  # 20 amino acids
        "MKWVTFISLLFLFSSAYS",     # 18 amino acids
        "A",                      # Single amino acid
        "ACDEFGHIKLMNPQRSTVWY"    # All 20 standard amino acids
    ]

    print("Testing protein sequences:\n")

    for i, seq in enumerate(test_sequences, 1):
        print(f"{i}. Sequence: {seq}")

        try:
            result = tu.run_one_function({
                "name": "protein_calculator",
                "arguments": {"sequence": seq}
            })

            if result.get("success"):
                print(f"   Molecular Weight: {result['molecular_weight']} Da")
                print(f"   Length: {result['sequence_length']} amino acids")
                print(f"   Cleaned: {result['sequence']}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"   Exception: {str(e)}")

        print()


def test_validation():
    """
    Test input validation with invalid sequences.
    """
    print("=== Testing Input Validation ===\n")

    # Note: The ProteinCalculator class is already defined in this file

    tool = ProteinCalculator()

    # Test cases for validation
    test_cases = [
        ("", "Empty sequence"),
        (None, "None sequence"),
        (123, "Non-string input"),
        ("ABCXYZ", "Invalid amino acid codes"),
        ("   ", "Whitespace only"),
        ("GIVEQCCTSICSLYQLENYCN", "Valid sequence")
    ]

    for test_input, description in test_cases:
        print(f"Testing {description}: {test_input}")

        try:
            tool.validate_input(sequence=test_input)
            print("   ✓ Validation passed")
        except ValueError as e:
            print(f"   ✗ Validation failed: {str(e)}")
        except Exception as e:
            print(f"   ✗ Unexpected error: {str(e)}")

        print()


if __name__ == "__main__":
    """
    Run the demonstration when this file is executed directly.
    """
    print("Protein Molecular Weight Calculator Tool")
    print("=======================================\n")

    # Test validation first
    test_validation()

    # Then demonstrate usage
    demonstrate_usage()

    print("\n=== How to Use This Tool ===")
    print("1. Save this file as 'protein_calculator.py'")
    print("2. Import it: from protein_calculator import ProteinCalculator")
    print("3. Use with ToolUniverse:")
    print("   tu = ToolUniverse()")
    print("   tu.load_tools()")
    print("   result = tu.run_one_function({")
    print("       'name': 'protein_calculator',")
    print("       'arguments': {'sequence': 'GIVEQCCTSICSLYQLENYCN'}")
    print("   })")
    print("\nFor more examples, see the ToolUniverse documentation!")
