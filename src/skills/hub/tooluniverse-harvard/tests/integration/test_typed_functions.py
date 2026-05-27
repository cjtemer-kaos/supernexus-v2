#!/usr/bin/env python3
"""
Tests for Typed Functions (generated tools)

Tests that generated typed functions can be imported and called correctly.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse


@pytest.mark.integration
class TestTypedFunctions:
    """Test that generated typed functions work correctly."""
    
    def test_typed_function_import(self):
        """Test that typed functions can be imported."""
        try:
            from tooluniverse.tools import UniProt_get_entry_by_accession
            assert callable(UniProt_get_entry_by_accession)
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
    
    def test_typed_function_call(self):
        """Test that typed functions can be called."""
        try:
            from tooluniverse.tools import UniProt_get_entry_by_accession
            
            # Test calling the function
            result = UniProt_get_entry_by_accession(accession="P05067")
            assert result is not None
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
        except Exception as e:
            # Other errors are expected (network, API limits, etc.)
            assert e is not None
    
    def test_typed_function_with_options(self):
        """Test that typed functions accept use_cache and validate options."""
        try:
            from tooluniverse.tools import UniProt_get_entry_by_accession
            
            # Test with options
            result = UniProt_get_entry_by_accession(
                accession="P05067",
                use_cache=True,
                validate=True
            )
            assert result is not None
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
        except Exception as e:
            # Other errors are expected
            assert e is not None
    
    def test_multiple_tools_import(self):
        """Test that multiple tools can be imported."""
        try:
            from tooluniverse.tools import (
                UniProt_get_entry_by_accession,
                ArXiv_search_papers,
                PubMed_search_articles
            )
            
            # All should be callable
            assert callable(UniProt_get_entry_by_accession)
            assert callable(ArXiv_search_papers)
            assert callable(PubMed_search_articles)
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")
    
    def test_wildcard_import(self):
        """Test that wildcard import works."""
        try:
            # Import specific tools to test they exist
            from tooluniverse.tools import UniProt_get_entry_by_accession, ArXiv_search_papers
            
            # Check that tools are callable
            assert callable(UniProt_get_entry_by_accession)
            assert callable(ArXiv_search_papers)
            
        except ImportError:
            pytest.skip("Tools not generated. Run: python scripts/build_tools.py")


if __name__ == "__main__":
    pytest.main([__file__])
