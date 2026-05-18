#!/usr/bin/env python3
"""
Agentic Tool Example

Demonstrates agentic tools available in ToolUniverse for AI-powered analysis
"""

from tooluniverse import ToolUniverse
from typing import Any, Dict, List

# =============================================================================
# Tool Initialization
# =============================================================================
# Description: Initialize ToolUniverse and load all available tools
# Syntax: tu = ToolUniverse(); tu.load_tools()
tu = ToolUniverse()
tu.load_tools()

# =============================================================================
# Sample Data Setup
# =============================================================================
# Description: Define sample biomedical text for testing agentic tools
# Note: This is example data for demonstrating tool capabilities
sample_abstract = """
Background: Drug-drug interactions (DDIs) are a major cause of adverse drug reactions and
represent a significant public health concern. This study aimed to develop and validate a
machine learning approach for predicting potential DDIs using molecular descriptors and
pharmacokinetic properties.

Methods: We collected data on 15,000 drug pairs from DrugBank and FDA databases. Molecular
descriptors were computed using RDKit, and pharmacokinetic parameters were extracted from
literature. A gradient boosting classifier was trained to predict DDI severity levels.

Results: The model achieved an accuracy of 89.2% with a precision of 0.91 and recall of 0.87
for high-severity DDI prediction. Feature importance analysis revealed that CYP450 enzyme
inhibition patterns and protein binding affinity were the most predictive features.

Conclusions: Our machine learning approach demonstrates high accuracy in predicting DDIs and
could serve as a valuable tool for clinical decision support and drug safety assessment.
"""

# =============================================================================
# Method 1: Experimental Design Scoring
# =============================================================================
# Description: Evaluate experimental design quality using AI analysis
# Syntax: tu.run({"name": "ExperimentalDesignScorer", "arguments": {"hypothesis": "...", "design_description": "..."}})
result1 = tu.run({
    "name": "ExperimentalDesignScorer",
    "arguments": {
        "hypothesis": "Daily high-intensity interval training (HIIT) for 8 weeks will improve insulin sensitivity in overweight adults compared to moderate-intensity continuous training (MICT).",
        "design_description": """
Study Design: Randomized, parallel-group clinical trial

Participants: 120 overweight adults (BMI 25–30) aged 30–50, sedentary lifestyle
Inclusion: No history of diabetes, stable weight for 3 months
Exclusion: Cardiovascular disease, musculoskeletal injuries, current exercise regimen

Interventions:
- HIIT group (n=60): 4×4-minute intervals at 90% HRmax with 3-minute active recovery, 3×/week
- MICT group (n=60): 40 minutes at 60% HRmax, 3×/week

Randomization: Computer-generated simple randomization
Blinding: Outcome assessors blinded

Primary Outcome: Change in HOMA-IR from baseline to 8 weeks
Secondary Outcomes: VO₂max, body composition (DXA), fasting glucose and insulin

Data Collection: Baseline, 4 weeks, 8 weeks
Sample Size Justification: 90% power to detect a 15% change in HOMA-IR (SD=20%), α=0.05, 15% dropout

Statistical Analysis: ANCOVA adjusting for baseline values, intention-to-treat
"""
    }
})

# =============================================================================
# Method 2: Biomedical Text Summarization
# =============================================================================
# Description: Summarize biomedical text using AI-powered analysis
# Syntax: tu.run({"name": "BiomedicalTextSummarizer", "arguments": {"text": "...", "summary_length": "...", "focus_area": "..."}})
result2 = tu.run({
    "name": "BiomedicalTextSummarizer",
    "arguments": {
        "text": sample_abstract,
        "summary_length": "100 words",
        "focus_area": "methodology and results"
    }
})

# =============================================================================
# Method 3: Short Text Summarization
# =============================================================================
# Description: Create concise summaries of short biomedical text
# Syntax: tu.run({"name": "BiomedicalTextSummarizer", "arguments": {"text": "...", "summary_length": "25 words", "focus_area": "..."}})
result3 = tu.run({
    "name": "BiomedicalTextSummarizer",
    "arguments": {
        "text": "Metformin is a first-line treatment for type 2 diabetes that works by reducing glucose production in the liver.",
        "summary_length": "25 words",
        "focus_area": "mechanism of action"
    }
})

# =============================================================================
# Method 4: Medical Literature Review
# =============================================================================
# Description: Review and analyze medical literature using AI
# Syntax: tu.run({"name": "MedicalLiteratureReviewer", "arguments": {"research_topic": "...", "literature_content": "...", "focus_area": "...", "study_types": "...", "quality_level": "...", "review_scope": "..."}})
result4 = tu.run({
    "name": "MedicalLiteratureReviewer",
    "arguments": {
        "research_topic": "Immunotherapy efficacy in triple-negative breast cancer",
        "literature_content": "Study 1: Pembrolizumab showed 23% response rate (n=150). Study 2: Atezolizumab combined with chemotherapy improved progression-free survival (HR=0.62, p=0.002).",
        "focus_area": "treatment efficacy",
        "study_types": "randomized controlled trials",
        "quality_level": "moderate and above",
        "review_scope": "rapid review"
    }
})

# =============================================================================
# Method 5: Hypothesis Generation
# =============================================================================
# Description: Generate research hypotheses using AI analysis
# Syntax: tu.run({"name": "HypothesisGenerator", "arguments": {"context": "...", "domain": "...", "number_of_hypotheses": "...", "hypothesis_format": "..."}})
result5 = tu.run({
    "name": "HypothesisGenerator",
    "arguments": {
        "context": "Recent studies have shown that patients with Alzheimer's disease have altered gut microbiome composition. Additionally, inflammation markers in the brain correlate with cognitive decline. Some research suggests that certain probiotics can cross the blood-brain barrier and influence neuroinflammation.",
        "domain": "neuroscience",
        "number_of_hypotheses": "3",
        "hypothesis_format": "If-then statements"
    }
})

# =============================================================================
# Method 6: Alternative Hypothesis Generation
# =============================================================================
# Description: Generate hypotheses in different domains
# Syntax: tu.run({"name": "HypothesisGenerator", "arguments": {"context": "...", "domain": "...", "number_of_hypotheses": "..."}})
result6 = tu.run({
    "name": "HypothesisGenerator",
    "arguments": {
        "context": "Machine learning models trained on electronic health records show promise in predicting drug adverse events. However, most models focus on single drugs rather than drug combinations. Polypharmacy is common in elderly patients and drug-drug interactions are poorly understood.",
        "domain": "pharmacology",
        "number_of_hypotheses": "2"
    }
})

# =============================================================================
# Method 7: Result Processing
# =============================================================================
# Description: Process and analyze agentic tool results
# Syntax: Check result structure and extract relevant information

# Process experimental design results
if isinstance(result1, dict):
    if result1.get("success"):
        result_text = result1["result"]
        # Access analysis results: result_text contains the evaluation
        pass
    else:
        # Handle failure case
        error_message = result1.get("error", "Unknown error")
        pass

# Process summarization results
if isinstance(result2, dict):
    if result2.get("success"):
        summary_text = result2["result"]
        # Access summary: summary_text contains the generated summary
        pass
    else:
        # Handle failure case
        error_message = result2.get("error", "Unknown error")
        pass

# =============================================================================
# Method 8: Metadata Extraction
# =============================================================================
# Description: Extract metadata from agentic tool results
# Syntax: Access metadata information from results

def extract_metadata(result):
    """Extract metadata from agentic tool results"""
    if isinstance(result, dict):
        metadata = result.get('metadata', {})
        model_info = metadata.get('model_info', {})
        return {
            'model_id': model_info.get('model_id', 'unknown'),
            'success': result.get('success', False),
            'error': result.get('error', None)
        }
    return {'model_id': 'unknown', 'success': False, 'error': 'Invalid result format'}

# Extract metadata from results
metadata1 = extract_metadata(result1)
metadata2 = extract_metadata(result2)
metadata3 = extract_metadata(result3)

# =============================================================================
# Method 9: Error Handling
# =============================================================================
# Description: Handle errors in agentic tool execution
# Syntax: Check for errors and handle appropriately

def handle_agentic_error(result, tool_name):
    """Handle errors from agentic tools"""
    if isinstance(result, dict):
        if not result.get("success", False):
            error_message = result.get("error", "Unknown error")
            # Handle specific error types
            if "timeout" in error_message.lower():
                # Handle timeout errors
                pass
            elif "invalid" in error_message.lower():
                # Handle invalid input errors
                pass
            else:
                # Handle other errors
                pass
            return False, error_message
        else:
            return True, "Success"
    return False, "Invalid result format"

# Handle errors for each result
success1, message1 = handle_agentic_error(result1, "ExperimentalDesignScorer")
success2, message2 = handle_agentic_error(result2, "BiomedicalTextSummarizer")
success3, message3 = handle_agentic_error(result3, "BiomedicalTextSummarizer")

# =============================================================================
# Method 10: Batch Processing
# =============================================================================
# Description: Process multiple agentic tools in sequence
# Syntax: Loop through multiple tool calls

agentic_queries = [
    {
        "name": "BiomedicalTextSummarizer",
        "arguments": {
            "text": "A brief description of a medical procedure",
            "summary_length": "50 words",
            "focus_area": "procedure steps"
        }
    },
    {
        "name": "HypothesisGenerator",
        "arguments": {
            "context": "A research context for hypothesis generation",
            "domain": "medicine",
            "number_of_hypotheses": "2"
        }
    }
]

batch_results = []
for query in agentic_queries:
    try:
        result = tu.run(query)
        batch_results.append(result)
    except Exception as e:
        # Handle individual query failures
        batch_results.append({"success": False, "error": str(e)})

# =============================================================================
# Summary of Agentic Tools
# =============================================================================
# Available agentic tools provide AI-powered analysis capabilities:
# - ExperimentalDesignScorer: Evaluate experimental design quality
# - BiomedicalTextSummarizer: Summarize biomedical text with focus areas
# - MedicalLiteratureReviewer: Review and analyze medical literature
# - HypothesisGenerator: Generate research hypotheses from context
# 
# Common result structure:
# - success: Boolean indicating if the operation succeeded
# - result: The actual analysis result (text content)
# - error: Error message if the operation failed
# - metadata: Additional information including model details
# 
# Error handling:
# - Check success field before processing results
# - Handle timeout errors for complex analyses
# - Validate input parameters before calling tools
# - Use appropriate text lengths for summarization
# 
# Performance considerations:
# - Agentic tools may take longer to execute
# - Use appropriate text lengths to avoid timeouts
# - Consider batch processing for multiple analyses
# - Handle individual tool failures gracefully
# 
# Use cases:
# - Research design evaluation
# - Literature analysis and summarization
# - Hypothesis generation for research
# - Medical text processing and analysis