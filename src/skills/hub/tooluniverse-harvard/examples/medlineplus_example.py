# test_medlineplus.py

from tooluniverse import ToolUniverse
import json

# Step 1: Initialize ToolUniverse and load all tools (including MedlinePlus tools)
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define example inputs
VALID_TERM_EN = "diabetes"  # English health topic keyword
VALID_DB_EN = "healthTopics"  # English health topics database
VALID_TERM_ES = "diabetes"  # Spanish health topic keyword
VALID_DB_ES = "healthTopicsSpanish"  # Spanish health topics database

# ICD-10 CM examples
VALID_CS_ICD10 = "2.16.840.1.113883.6.90"
VALID_CODE_ICD10 = "E11.9"  # Diabetes without complications

# RXCUI examples
VALID_CS_RXCUI = "2.16.840.1.113883.6.88"
VALID_CODE_RXCUI = "637188"  # RXCUI for Chantix
VALID_DN_RXCUI = "Chantix 0.5 MG Oral Tablet"

# Genetics examples
VALID_CONDITION = "alzheimer-disease"  # Genetic condition URL slug
VALID_GENE = "BRCA1"  # Gene URL slug

# Invalid examples
INVALID_TERM = ""  # Empty keyword
INVALID_CS = "INVALID_CS"  # Invalid code system
INVALID_CODE = "INVALID_CODE"  # Invalid code value


def print_result(result, tool_name):
    """Print formatted results"""
    if isinstance(result, dict):
        if "error" in result:
            print("⚠️ Error:", result["error"])
            if "detail" in result:
                print("Detail:", result["detail"])
            return

        # Define output formats
        formats = {
            "MedlinePlus_search_topics_by_keyword": {
                "title": "📚 Health Topic Search Results",
                "items": "topics",
                "fields": {
                    "title": "Title",
                    "meta_desc": "Description",
                    "url": "Link",
                    "language": "Language",
                    "rank": "Rank",
                    "also_called": "Also Known As",
                    "summary": "Detailed Summary",
                    "groups": "Categories",
                },
            },
            "MedlinePlus_connect_lookup_by_code": {
                "title": "🔍 Code Lookup Results",
                "items": "responses",
                "fields": {"title": "Title", "summary": "Summary", "url": "Link"},
            },
            "MedlinePlus_get_genetics_condition_by_name": {
                "title": "🧬 Genetic Condition Information",
                "fields": {
                    "name": "Condition Name",
                    "description": "Description",
                    "genes": "Related Genes",
                    "synonyms": "Synonyms",
                    "ghr_page": "Detailed Information Page",
                },
            },
            "MedlinePlus_get_genetics_gene_by_name": {
                "title": "🧬 Gene Information",
                "fields": {
                    "name": "Gene Name",
                    "function": "Function Description",
                    "health_conditions": "Related Health Conditions",
                    "synonyms": "Synonyms",
                    "ghr_page": "Detailed Information Page",
                },
            },
            "MedlinePlus_get_genetics_index": {
                "title": "📋 Genetics Topics List",
                "items": "topics",
                "fields": {"name": "Name", "url": "Link"},
            },
        }

        # Get tool output format
        fmt = formats.get(tool_name, {})
        if not fmt:
            print("\nRaw Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        # Print title
        print(f"\n{fmt['title']}:")

        # Handle list type responses
        if "items" in fmt:
            items = result.get(fmt["items"], [])
            if not items:
                print("No related content found")
                return
            for i, item in enumerate(items, 1):
                print(f"\n{i}. {item.get(list(fmt['fields'].keys())[0], '')}")
                for field, label in fmt["fields"].items():
                    value = item.get(field, "")
                    if isinstance(value, list):
                        print(f"   {label}:")
                        for v in value:
                            print(f"   - {v}")
                    else:
                        print(f"   {label}: {value}")
            return

        # Handle dictionary type responses
        for field, label in fmt["fields"].items():
            value = result.get(field, "")
            if isinstance(value, list):
                print(f"\n{label}:")
                for item in value:
                    print(f"- {item}")
            else:
                print(f"\n{label}: {value}")

    elif isinstance(result, str):
        print("\nRaw Response Text:")
        print(result)
    else:
        print("\nOther Type Response:")
        print(result)


# Step 3: Define test case list
test_queries = [
    # Health topic search - using simpler search terms
    {
        "name": "MedlinePlus_search_topics_by_keyword",
        "arguments": {"term": "heart", "db": "healthTopics", "rettype": "topic"},
    },
    {
        "name": "MedlinePlus_search_topics_by_keyword",
        "arguments": {"term": "diabetes", "db": "healthTopics", "rettype": "topic"},
    },
    {
        "name": "MedlinePlus_search_topics_by_keyword",
        "arguments": {"term": "cancer", "db": "healthTopics", "rettype": "brief"},
    },
    {
        "name": "MedlinePlus_search_topics_by_keyword",
        "arguments": {
            "term": "diabetes",
            "db": "healthTopicsSpanish",
            "rettype": "topic",
        },
    },
    # Code lookup
    {
        "name": "MedlinePlus_connect_lookup_by_code",
        "arguments": {
            "cs": "2.16.840.1.113883.6.90",
            "c": "E11.9",
            "language": "en",
            "format": "json",
        },
    },
    {
        "name": "MedlinePlus_connect_lookup_by_code",
        "arguments": {
            "cs": "2.16.840.1.113883.6.88",
            "c": "637188",
            "dn": "Chantix 0.5 MG Oral Tablet",
            "language": "en",
            "format": "xml",
        },
    },
    # Genetics information
    {
        "name": "MedlinePlus_get_genetics_condition_by_name",
        "arguments": {"condition": "alzheimer-disease", "format": "json"},
    },
    {
        "name": "MedlinePlus_get_genetics_gene_by_name",
        "arguments": {"gene": "BRCA1", "format": "json"},
    },
    {"name": "MedlinePlus_get_genetics_index", "arguments": {}},
    # Error testing
    {
        "name": "MedlinePlus_search_topics_by_keyword",
        "arguments": {"term": "", "db": "healthTopics", "rettype": "topic"},
    },
    {
        "name": "MedlinePlus_connect_lookup_by_code",
        "arguments": {
            "cs": "INVALID_CS",
            "c": "INVALID_CODE",
            "language": "en",
            "format": "json",
        },
    },
]

# Step 4: Loop through all test cases and print example output
for idx, query in enumerate(test_queries):
    print(f"\n{'='*80}")
    print(f"[{idx+1}] Running tool: {query['name']}")
    print(f"Arguments: {query['arguments']}")
    print(f"{'='*80}")

    try:
        result = tooluni.run(query)
        print_result(result, query["name"])
    except Exception as e:
        print("⚠️ Exception:", e)

print("\n🎉 MedlinePlus Testing Complete!")
