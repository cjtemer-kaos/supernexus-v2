"""
OpenRouter Integration Example
===============================

This example demonstrates how to use OpenRouter with ToolUniverse to access
models from multiple providers (OpenAI, Anthropic, Google, Qwen) through a
single unified API.

Requirements:
- OpenRouter API key (get from https://openrouter.ai/)
- Set OPENROUTER_API_KEY environment variable
"""

import os
import json
from tooluniverse import ToolUniverse


def setup_openrouter():
    """Set up OpenRouter API key (replace with your actual key)."""
    # Check if already set
    if not os.getenv("OPENROUTER_API_KEY"):
        # In production, use environment variables or secure storage
        # os.environ["OPENROUTER_API_KEY"] = "your_key_here"
        print("⚠️  Please set OPENROUTER_API_KEY environment variable")
        print("   export OPENROUTER_API_KEY='your_key_here'")
        return False
    
    # Optional: Set site attribution for tracking
    if not os.getenv("OPENROUTER_SITE_URL"):
        os.environ["OPENROUTER_SITE_URL"] = "https://github.com/your-username/your-project"
    if not os.getenv("OPENROUTER_SITE_NAME"):
        os.environ["OPENROUTER_SITE_NAME"] = "ToolUniverse Example"
    
    return True


def example_1_basic_openai_gpt4o():
    """Example 1: Basic usage with OpenAI GPT-4o via OpenRouter."""
    print("\n" + "="*70)
    print("Example 1: Using OpenAI GPT-4o via OpenRouter")
    print("="*70)
    
    tu = ToolUniverse()
    
    # Create a simple summarization tool using GPT-4o
    tool_config = {
        "name": "GPT4o_Summarizer",
        "description": "Summarize text using OpenAI GPT-4o via OpenRouter",
        "type": "AgenticTool",
        "prompt": "Provide a concise summary of the following text in 2-3 sentences:\n\n{text}",
        "input_arguments": ["text"],
        "parameter": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to summarize",
                    "required": True
                }
            },
            "required": ["text"]
        },
        "configs": {
            "api_type": "OPENROUTER",
            "model_id": "openai/gpt-4o",
            "temperature": 0.3,
            "return_json": False,
            "return_metadata": True
        }
    }
    
    # Register and use the tool
    tu.register_tool_from_config(tool_config)
    
    sample_text = """
    Artificial intelligence has made remarkable progress in recent years, with
    large language models demonstrating unprecedented capabilities in natural
    language understanding and generation. These models can perform a wide range
    of tasks including translation, summarization, question answering, and even
    creative writing. However, challenges remain in areas such as factual accuracy,
    reasoning capabilities, and computational efficiency.
    """
    
    result = tu.execute_tool("GPT4o_Summarizer", {"text": sample_text})
    
    print("\n📝 Input Text:")
    print(sample_text.strip())
    print("\n✨ Summary:")
    if isinstance(result, dict) and "result" in result:
        print(result["result"])
        print(f"\n⏱️  Execution time: {result.get('metadata', {}).get('execution_time_seconds', 'N/A')}s")
    else:
        print(result)


def example_2_anthropic_claude():
    """Example 2: Using Anthropic Claude 3.5 Sonnet for analysis."""
    print("\n" + "="*70)
    print("Example 2: Using Anthropic Claude 3.5 Sonnet via OpenRouter")
    print("="*70)
    
    tu = ToolUniverse()
    
    # Create an analysis tool using Claude
    tool_config = {
        "name": "Claude_Analyzer",
        "description": "Analyze scientific concepts using Claude 3.5 Sonnet",
        "type": "AgenticTool",
        "prompt": """Analyze the following scientific concept and provide:
1. A clear explanation
2. Key applications
3. Current research directions

Concept: {concept}

Provide a structured analysis.""",
        "input_arguments": ["concept"],
        "parameter": {
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "Scientific concept to analyze",
                    "required": True
                }
            },
            "required": ["concept"]
        },
        "configs": {
            "api_type": "OPENROUTER",
            "model_id": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "return_json": False,
            "return_metadata": True
        }
    }
    
    tu.register_tool_from_config(tool_config)
    
    result = tu.execute_tool("Claude_Analyzer", {
        "concept": "CRISPR gene editing"
    })
    
    print("\n🔬 Concept: CRISPR gene editing")
    print("\n📊 Analysis:")
    if isinstance(result, dict) and "result" in result:
        print(result["result"])
    else:
        print(result)


def example_3_google_gemini():
    """Example 3: Using Google Gemini 2.0 Flash for large context tasks."""
    print("\n" + "="*70)
    print("Example 3: Using Google Gemini 2.0 Flash via OpenRouter")
    print("="*70)
    
    tu = ToolUniverse()
    
    tool_config = {
        "name": "Gemini_Extractor",
        "description": "Extract key information using Gemini 2.0 Flash",
        "type": "AgenticTool",
        "prompt": """Extract the following information from the research paper abstract:
- Main objective
- Methods used
- Key findings
- Significance

Abstract: {abstract}

Provide structured JSON output.""",
        "input_arguments": ["abstract"],
        "parameter": {
            "type": "object",
            "properties": {
                "abstract": {
                    "type": "string",
                    "description": "Research paper abstract",
                    "required": True
                }
            },
            "required": ["abstract"]
        },
        "configs": {
            "api_type": "OPENROUTER",
            "model_id": "google/gemini-2.0-flash-exp",
            "temperature": 0.2,
            "return_json": True,
            "return_metadata": True
        }
    }
    
    tu.register_tool_from_config(tool_config)
    
    abstract = """
    We present AlphaFold 2, a deep learning system that predicts protein 3D structures
    from amino acid sequences with unprecedented accuracy. The system combines evolutionary,
    physical, and geometric constraints to predict structures that are competitive with
    experimental results. On the CASP14 assessment, AlphaFold 2 achieved a median GDT_TS
    score of 92.4 across all targets, representing a significant advance over previous
    methods. This breakthrough has major implications for structural biology, drug discovery,
    and our understanding of protein function.
    """
    
    result = tu.execute_tool("Gemini_Extractor", {"abstract": abstract})
    
    print("\n📄 Abstract:")
    print(abstract.strip())
    print("\n🔍 Extracted Information:")
    if isinstance(result, dict) and "result" in result:
        try:
            parsed = json.loads(result["result"]) if isinstance(result["result"], str) else result["result"]
            print(json.dumps(parsed, indent=2))
        except:
            print(result["result"])
    else:
        print(result)


def example_4_qwen_reasoning():
    """Example 4: Using Qwen QwQ for reasoning tasks."""
    print("\n" + "="*70)
    print("Example 4: Using Qwen QwQ-32B for Reasoning")
    print("="*70)
    
    tu = ToolUniverse()
    
    tool_config = {
        "name": "Qwen_Reasoner",
        "description": "Solve reasoning problems using Qwen QwQ",
        "type": "AgenticTool",
        "prompt": """Solve the following problem step by step:

{problem}

Show your reasoning process and provide the final answer.""",
        "input_arguments": ["problem"],
        "parameter": {
            "type": "object",
            "properties": {
                "problem": {
                    "type": "string",
                    "description": "Problem to solve",
                    "required": True
                }
            },
            "required": ["problem"]
        },
        "configs": {
            "api_type": "OPENROUTER",
            "model_id": "qwen/qwq-32b-preview",
            "temperature": 0.1,
            "return_json": False,
            "return_metadata": True
        }
    }
    
    tu.register_tool_from_config(tool_config)
    
    problem = """
    A pharmaceutical company is testing a new drug. In a clinical trial:
    - 1000 patients received the drug
    - 850 showed improvement
    - 150 showed no change
    - Of those who improved, 20% experienced minor side effects
    
    Calculate:
    1. Success rate (percentage)
    2. Number of patients with side effects
    3. Overall risk-benefit ratio interpretation
    """
    
    result = tu.execute_tool("Qwen_Reasoner", {"problem": problem})
    
    print("\n❓ Problem:")
    print(problem.strip())
    print("\n💡 Solution:")
    if isinstance(result, dict) and "result" in result:
        print(result["result"])
    else:
        print(result)


def example_5_tool_finder_with_openrouter():
    """Example 5: Using ToolFinderLLM with OpenRouter models."""
    print("\n" + "="*70)
    print("Example 5: Tool Finder with OpenRouter")
    print("="*70)
    
    tu = ToolUniverse()
    
    # Create a custom ToolFinderLLM with OpenRouter
    finder_config = {
        "type": "ToolFinderLLM",
        "name": "Tool_Finder_OpenRouter",
        "description": "Find tools using OpenRouter Claude",
        "configs": {
            "api_type": "OPENROUTER",
            "model_id": "anthropic/claude-3.5-sonnet",
            "temperature": 0.1,
            "max_new_tokens": 4096,
            "return_json": True,
            "exclude_tools": ["Tool_RAG", "Tool_Finder", "Finish", "CallAgent"]
        }
    }
    
    tu.register_tool_from_config(finder_config)
    
    # Search for protein-related tools
    result = tu.execute_tool("Tool_Finder_OpenRouter", {
        "description": "tools for protein structure prediction and analysis",
        "limit": 5
    })
    
    print("\n🔍 Query: 'tools for protein structure prediction and analysis'")
    print("\n📋 Found Tools:")
    
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            for i, tool in enumerate(parsed.get("tools", []), 1):
                print(f"\n{i}. {tool.get('name', 'Unknown')}")
                print(f"   Type: {tool.get('type', 'Unknown')}")
                print(f"   Description: {tool.get('description', 'No description')[:100]}...")
        except:
            print(result)
    else:
        print(result)


def example_6_model_comparison():
    """Example 6: Compare responses from different models."""
    print("\n" + "="*70)
    print("Example 6: Comparing Different OpenRouter Models")
    print("="*70)
    
    tu = ToolUniverse()
    
    # Prompt to test
    test_prompt = "Explain quantum entanglement in one paragraph suitable for a high school student."
    
    # Models to compare
    models = [
        ("openai/gpt-4o", "OpenAI GPT-4o"),
        ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
        ("google/gemini-2.0-flash-exp", "Gemini 2.0 Flash"),
        ("qwen/qwen-2.5-72b-instruct", "Qwen 2.5 72B"),
    ]
    
    print(f"\n📝 Prompt: {test_prompt}")
    print("\n" + "="*70)
    
    for model_id, model_name in models:
        print(f"\n🤖 {model_name} ({model_id}):")
        print("-" * 70)
        
        tool_config = {
            "name": f"Explainer_{model_id.replace('/', '_')}",
            "description": f"Explain concepts using {model_name}",
            "type": "AgenticTool",
            "prompt": "{text}",
            "input_arguments": ["text"],
            "parameter": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "required": True}
                },
                "required": ["text"]
            },
            "configs": {
                "api_type": "OPENROUTER",
                "model_id": model_id,
                "temperature": 0.7,
                "return_json": False,
                "return_metadata": False
            }
        }
        
        try:
            tu.register_tool_from_config(tool_config)
            result = tu.execute_tool(tool_config["name"], {"text": test_prompt})
            print(result if isinstance(result, str) else result.get("result", str(result)))
        except Exception as e:
            print(f"❌ Error: {str(e)}")


def example_7_fallback_configuration():
    """Example 7: Configure automatic fallback between models."""
    print("\n" + "="*70)
    print("Example 7: Automatic Fallback Between Models")
    print("="*70)
    
    tu = ToolUniverse()
    
    # Configure tool with explicit fallback
    tool_config = {
        "name": "Robust_Analyzer",
        "description": "Analyzer with automatic fallback",
        "type": "AgenticTool",
        "prompt": "Analyze this statement: {statement}",
        "input_arguments": ["statement"],
        "parameter": {
            "type": "object",
            "properties": {
                "statement": {"type": "string", "required": True}
            },
            "required": ["statement"]
        },
        "configs": {
            "api_type": "OPENROUTER",
            "model_id": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "return_json": False,
            # Explicit fallback configuration
            "fallback_api_type": "OPENROUTER",
            "fallback_model_id": "openai/gpt-4o",
            "use_global_fallback": True,  # Also use global fallback chain
            "return_metadata": True
        }
    }
    
    tu.register_tool_from_config(tool_config)
    
    result = tu.execute_tool("Robust_Analyzer", {
        "statement": "The integration of AI in scientific research is transforming how we approach complex problems."
    })
    
    print("\n💪 Fallback Configuration:")
    print("  Primary: Claude 3.5 Sonnet")
    print("  Fallback 1: GPT-4o")
    print("  Fallback 2: Global chain (configured in environment)")
    
    print("\n✅ Result:")
    if isinstance(result, dict):
        print(result.get("result", str(result)))
        if "metadata" in result:
            model_info = result["metadata"].get("model_info", {})
            print(f"\n📊 Used Model: {model_info.get('model_id', 'Unknown')}")
            print(f"   API Type: {model_info.get('api_type', 'Unknown')}")
    else:
        print(result)


def main():
    """Run all examples."""
    print("="*70)
    print("OpenRouter Integration Examples for ToolUniverse")
    print("="*70)
    
    # Setup
    if not setup_openrouter():
        print("\n❌ OpenRouter API key not configured. Please set it and try again.")
        return
    
    print("\n✅ OpenRouter configured successfully!")
    print("\nRunning examples...")
    
    try:
        # Run examples
        example_1_basic_openai_gpt4o()
        example_2_anthropic_claude()
        example_3_google_gemini()
        example_4_qwen_reasoning()
        example_5_tool_finder_with_openrouter()
        example_6_model_comparison()
        example_7_fallback_configuration()
        
        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


