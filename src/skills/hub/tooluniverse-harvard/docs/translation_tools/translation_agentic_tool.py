#!/usr/bin/env python3
"""
Translation Agentic Tool for ToolUniverse

This script demonstrates how to create and use an AgenticTool for translation
without modifying the source code. It uses the ToolUniverse framework to
register and execute a translation tool.

Author: ToolUniverse Community
Date: 2024
"""

import os
import sys
import json
import polib
from pathlib import Path
from typing import Dict, Any, List

# Add the src directory to the path so we can import ToolUniverse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tooluniverse import ToolUniverse
from tooluniverse.agentic_tool import AgenticTool


class TranslationAgenticTool:
    """
    A wrapper class that demonstrates how to use AgenticTool for translation
    without modifying the ToolUniverse source code.
    """
    
    def __init__(self):
        """Initialize the translation tool."""
        self.tu = None
        self.translation_tool = None
        self._setup_tool()
    
    def _setup_tool(self):
        """Set up the AgenticTool for translation."""
        # Define the tool configuration
        tool_config = {
            "name": "translation_agentic_tool",
            "type": "AgenticTool",
            "description": "AI-powered translation tool for translating documentation from English to Chinese",
            "prompt": """You are an expert translator specializing in technical documentation translation from English to Chinese.

Your task is to translate the provided English text into natural, fluent Chinese while maintaining:
1. Technical accuracy and terminology consistency
2. Natural Chinese language flow
3. Proper context understanding
4. Professional documentation tone

English text to translate: {text}

Context (if provided): {context}

Please provide only the Chinese translation without any additional explanations or formatting.""",
            "input_arguments": ["text", "context"],
            "parameter": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The English text to translate to Chinese",
                        "required": True
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context to help with translation accuracy",
                        "required": False,
                        "default": ""
                    }
                },
                "required": ["text"]
            },
            "configs": {
                "api_type": "CHATGPT",
                "model_id": "gpt-4o-mini",
                "temperature": 0.3,
                "max_new_tokens": 2048,
                "return_json": False
            }
        }
        
        # Initialize ToolUniverse
        self.tu = ToolUniverse()
        
        # Create the AgenticTool instance
        self.translation_tool = AgenticTool(tool_config)
        
        print("✅ Translation AgenticTool initialized successfully!")
    
    def translate_text(self, text: str, context: str = "") -> str:
        """
        Translate English text to Chinese using the AgenticTool.
        
        Args:
            text: English text to translate
            context: Optional context for better translation
            
        Returns:
            Translated Chinese text
        """
        try:
            # Use the AgenticTool to translate
            result = self.translation_tool.run({"text": text, "context": context})
            
            if isinstance(result, str):
                return result.strip()
            elif isinstance(result, dict) and result.get("success", False):
                # Handle the actual return format from AgenticTool
                return result.get("result", "").strip()
            else:
                print(f"❌ Translation failed: {result}")
                return text  # Return original text if translation fails
                
        except Exception as e:
            print(f"❌ Error during translation: {str(e)}")
            return text  # Return original text if translation fails
    
    def find_untranslated_entries(self, po_file_path: str) -> List[Dict[str, Any]]:
        """
        Find all untranslated entries in a .po file.
        
        Args:
            po_file_path: Path to the .po file
            
        Returns:
            List of untranslated entries
        """
        try:
            po = polib.pofile(po_file_path)
            untranslated = []
            
            for entry in po:
                if not entry.msgstr and entry.msgid:
                    untranslated.append({
                        "msgid": entry.msgid,
                        "msgstr": entry.msgstr,
                        "linenum": entry.linenum,
                        "comment": entry.comment
                    })
            
            return untranslated
            
        except Exception as e:
            print(f"❌ Error reading .po file {po_file_path}: {str(e)}")
            return []
    
    def update_po_file(self, po_file_path: str, translations: List[Dict[str, Any]]) -> bool:
        """
        Update a .po file with new translations.
        
        Args:
            po_file_path: Path to the .po file
            translations: List of translations to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            po = polib.pofile(po_file_path)
            
            # Create a mapping of msgid to translation
            translation_map = {t["msgid"]: t["msgstr"] for t in translations}
            
            # Update entries
            updated_count = 0
            for entry in po:
                if entry.msgid in translation_map:
                    entry.msgstr = translation_map[entry.msgid]
                    updated_count += 1
            
            # Save the file
            po.save()
            print(f"✅ Updated {updated_count} entries in {po_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating .po file {po_file_path}: {str(e)}")
            return False
    
    def translate_po_file(self, po_file_path: str, context: str = "") -> bool:
        """
        Translate all untranslated entries in a .po file.
        
        Args:
            po_file_path: Path to the .po file
            context: Optional context for better translation
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🔄 Processing {po_file_path}...")
        
        # Find untranslated entries
        untranslated = self.find_untranslated_entries(po_file_path)
        
        if not untranslated:
            print(f"✅ No untranslated entries found in {po_file_path}")
            return True
        
        print(f"📝 Found {len(untranslated)} untranslated entries")
        
        # Translate each entry
        translations = []
        for i, entry in enumerate(untranslated, 1):
            print(f"🔄 Translating entry {i}/{len(untranslated)}: {entry['msgid'][:50]}...")
            
            translated_text = self.translate_text(entry['msgid'], context)
            
            if translated_text and translated_text != entry['msgid']:
                translations.append({
                    "msgid": entry['msgid'],
                    "msgstr": translated_text,
                    "linenum": entry['linenum']
                })
                print(f"✅ Translated: {translated_text[:50]}...")
            else:
                print(f"⚠️  Skipped (no translation or same as original)")
        
        # Update the .po file
        if translations:
            return self.update_po_file(po_file_path, translations)
        else:
            print("⚠️  No translations to apply")
            return True
    
    def batch_translate_directory(self, directory_path: str, context: str = "") -> Dict[str, bool]:
        """
        Translate all .po files in a directory.
        
        Args:
            directory_path: Path to directory containing .po files
            context: Optional context for better translation
            
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        po_files = list(Path(directory_path).rglob("*.po"))
        
        if not po_files:
            print(f"❌ No .po files found in {directory_path}")
            return results
        
        print(f"📁 Found {len(po_files)} .po files to process")
        
        for po_file in po_files:
            print(f"\n{'='*60}")
            print(f"Processing: {po_file}")
            print(f"{'='*60}")
            
            success = self.translate_po_file(str(po_file), context)
            results[str(po_file)] = success
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        print(f"\n📊 Summary: {successful}/{len(results)} files processed successfully")
        
        return results


def main():
    """Main function to demonstrate the translation tool."""
    print("🚀 Translation AgenticTool Demo")
    print("=" * 50)
    
    # Initialize the translation tool
    translator = TranslationAgenticTool()
    
    # Example 1: Translate a single text
    print("\n📝 Example 1: Single text translation")
    print("-" * 40)
    
    sample_text = "Welcome to ToolUniverse - your comprehensive toolkit for scientific research and data analysis."
    context = "This is a welcome message for a scientific software toolkit"
    
    translated = translator.translate_text(sample_text, context)
    print(f"Original: {sample_text}")
    print(f"Translated: {translated}")
    
    # Example 2: Process a .po file (if exists)
    print("\n📁 Example 2: .po file processing")
    print("-" * 40)
    
    # Look for .po files in the locale directory
    locale_dir = Path(__file__).parent / "locale" / "zh_CN" / "LC_MESSAGES"
    
    if locale_dir.exists():
        po_files = list(locale_dir.rglob("*.po"))
        if po_files:
            # Process the first .po file as an example
            sample_po = po_files[0]
            print(f"Processing sample file: {sample_po}")
            
            # Show untranslated entries
            untranslated = translator.find_untranslated_entries(str(sample_po))
            print(f"Found {len(untranslated)} untranslated entries")
            
            if untranslated:
                # Show first few untranslated entries
                for i, entry in enumerate(untranslated[:3]):
                    print(f"  {i+1}. {entry['msgid'][:100]}...")
                
                # Ask user if they want to translate
                response = input(f"\nDo you want to translate {len(untranslated)} entries? (y/N): ")
                if response.lower() == 'y':
                    translator.translate_po_file(str(sample_po), "Documentation translation")
        else:
            print("No .po files found in locale directory")
    else:
        print("Locale directory not found")
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    main()
